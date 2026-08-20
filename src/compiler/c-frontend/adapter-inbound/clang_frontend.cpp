// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Pinned-Clang adaptation into the version-one normalized C frontend form.
// - Must-Not:
//   - Serialize Clang addresses, host paths, raw dump nodes, or native layout.
// - Allows:
//   - Inputs: one in-memory C translation unit and private include roots.
//   - Outputs: stable source-relative semantic nodes and normalized C types.
//   - Side effects: Clang parsing and diagnostics inside the current process.
// - Split-When:
//   - Multi-translation-unit symbol resolution gains independent lifecycle.
// - Merge-When:
//   - Clang remains the sole inbound C semantic frontend implementation.
// - Summary:
//   - Converts exact Clang 22.1.8 AST semantics into repository-owned JSON.
// - Description:
//   - Semantic preorder includes implicit conversions but filters header nodes.
// - Usage:
//   - Called through the host-neutral frontend port by native composition.
// - Defaults:
//   - Unknown AST/type classes fail closed with MALBOLGE-FRONTEND diagnostics.
//

//! Pinned-Clang implementation of deterministic C frontend normalization.

#include "../port-inbound/frontend.hpp"

#include "clang/AST/ASTConsumer.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/Decl.h"
#include "clang/AST/Expr.h"
#include "clang/AST/RecursiveASTVisitor.h"
#include "clang/Basic/SourceManager.h"
#include "clang/Basic/TypeTraits.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendAction.h"
#include "clang/Lex/Lexer.h"
#include "clang/Tooling/Tooling.h"
#include "llvm/ADT/APFloat.h"
#include "llvm/ADT/APInt.h"
#include "llvm/ADT/APSInt.h"
#include "llvm/ADT/ArrayRef.h"
#include "llvm/ADT/SmallString.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/SHA256.h"
#include "llvm/Support/raw_ostream.h"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace malbolge::compiler::c_frontend {
namespace {

constexpr char kArtifactId[] = "malbolge-c-frontend-v1";
constexpr char kAbiId[] = "malbolge-c32-v1";
constexpr char kClangTarget[] = "wasm32-unknown-unknown";
constexpr char kClangVersion[] = "22.1.8";
constexpr char kLanguage[] = "c23";
constexpr char kTargetProfile[] = "malbolge-2026";

struct Position final {
  std::uint64_t byte = 0;
  unsigned column = 0;
  unsigned line = 0;
};

struct Span final {
  Position begin;
  Position end;
};

struct Node final {
  std::optional<std::string> constant_integer;
  std::optional<std::string> definition;
  std::optional<bool> enum_fixed;
  std::optional<std::string> enum_underlying;
  std::size_t id = 0;
  std::optional<bool> inline_specified;
  std::string kind;
  std::optional<std::string> linkage;
  std::optional<std::string> literal;
  std::optional<std::string> name;
  std::optional<std::string> operation;
  std::size_t parent = 0;
  std::optional<std::string> reference;
  Span span;
  std::optional<std::string> storage_class;
  std::optional<std::string> storage_duration;
  std::optional<std::string> type;
};

[[nodiscard]] std::string hex_bytes(llvm::ArrayRef<std::uint8_t> bytes) {
  constexpr char alphabet[] = "0123456789abcdef";
  std::string result;
  result.reserve(bytes.size() * 2U);
  for (const std::uint8_t byte : bytes) {
    result.push_back(alphabet[byte >> 4U]);
    result.push_back(alphabet[byte & 0x0fU]);
  }
  return result;
}

[[nodiscard]] std::string source_sha256(std::string_view source) {
  llvm::SHA256 digest;
  digest.update(llvm::StringRef(source.data(), source.size()));
  const auto bytes = digest.final();
  return hex_bytes(bytes);
}

[[nodiscard]] std::string apsint_text(const llvm::APSInt &value) {
  llvm::SmallString<64> buffer;
  value.toString(buffer, 10);
  return std::string(buffer);
}

[[nodiscard]] std::string apint_hex(const llvm::APInt &value) {
  llvm::SmallString<128> buffer;
  value.toString(buffer, 16, false);
  const std::size_t digits = (value.getBitWidth() + 3U) / 4U;
  std::string result(buffer);
  if (result.size() < digits) {
    result.insert(0, digits - result.size(), '0');
  }
  return result;
}

class Normalizer final : public clang::RecursiveASTVisitor<Normalizer> {
public:
  explicit Normalizer(clang::ASTContext &context)
      : context_(context), source_manager_(context.getSourceManager()) {}

  [[nodiscard]] const std::string &failure() const { return failure_; }

  [[nodiscard]] const std::vector<Node> &nodes() const { return nodes_; }

  bool TraverseDecl(clang::Decl *declaration) {
    if (declaration == nullptr) {
      return true;
    }
    if (llvm::isa<clang::TranslationUnitDecl>(declaration)) {
      return Base::TraverseDecl(declaration);
    }
    const bool record =
        should_record(declaration->getLocation()) && !declaration->isImplicit();
    std::optional<std::size_t> node_id;
    if (record) {
      node_id = append_declaration(*declaration);
      if (!node_id.has_value()) {
        return false;
      }
      parents_.push_back(*node_id);
    }
    const bool traversed = Base::TraverseDecl(declaration);
    if (node_id.has_value()) {
      parents_.pop_back();
    }
    return traversed;
  }

  bool TraverseStmt(clang::Stmt *statement) {
    if (statement == nullptr) {
      return true;
    }
    const bool record = should_record(statement->getBeginLoc());
    std::optional<std::size_t> node_id;
    if (record) {
      node_id = append_statement(*statement);
      if (!node_id.has_value()) {
        return false;
      }
      parents_.push_back(*node_id);
    }
    const bool traversed = Base::TraverseStmt(statement);
    if (node_id.has_value()) {
      parents_.pop_back();
    }
    return traversed;
  }

private:
  using Base = clang::RecursiveASTVisitor<Normalizer>;

  [[nodiscard]] std::optional<std::string>
  normalize_type(clang::QualType input) {
    if (input.isNull()) {
      return std::nullopt;
    }
    clang::QualType canonical = input.getCanonicalType();
    if (canonical.hasAddressSpace() &&
        canonical.getAddressSpace() != clang::LangAS::Default) {
      fail_type(*canonical.getTypePtr(), "non-default-address-space");
      return std::nullopt;
    }
    const clang::Qualifiers qualifiers = canonical.getQualifiers();
    canonical = canonical.getUnqualifiedType();
    const clang::Type *type = canonical.getTypePtr();
    std::optional<std::string> core = normalize_unqualified_type(*type);
    if (!core.has_value()) {
      return std::nullopt;
    }
    std::vector<std::string_view> names;
    if (qualifiers.hasConst()) {
      names.emplace_back("const");
    }
    if (qualifiers.hasRestrict()) {
      names.emplace_back("restrict");
    }
    if (qualifiers.hasVolatile()) {
      names.emplace_back("volatile");
    }
    if (names.empty()) {
      return core;
    }
    std::string result = "q[";
    for (std::size_t index = 0; index < names.size(); ++index) {
      if (index != 0U) {
        result.push_back(',');
      }
      result.append(names[index]);
    }
    result.append("](");
    result.append(*core);
    result.push_back(')');
    return result;
  }

  [[nodiscard]] std::optional<std::string>
  normalize_unqualified_type(const clang::Type &type) {
    if (const auto *builtin = llvm::dyn_cast<clang::BuiltinType>(&type)) {
      return normalize_builtin(*builtin);
    }
    if (const auto *pointer = llvm::dyn_cast<clang::PointerType>(&type)) {
      return wrap_type("ptr(", pointer->getPointeeType(), ")");
    }
    if (const auto *array = llvm::dyn_cast<clang::ConstantArrayType>(&type)) {
      auto element = normalize_type(array->getElementType());
      if (!element.has_value()) {
        return std::nullopt;
      }
      llvm::SmallString<64> size;
      array->getSize().toString(size, 10, false);
      return "array[" + std::string(size) + "](" + *element + ")";
    }
    if (const auto *array = llvm::dyn_cast<clang::IncompleteArrayType>(&type)) {
      return wrap_type("incomplete-array(", array->getElementType(), ")");
    }
    if (const auto *array = llvm::dyn_cast<clang::VariableArrayType>(&type)) {
      return wrap_type("vla(", array->getElementType(), ")");
    }
    if (const auto *function =
            llvm::dyn_cast<clang::FunctionProtoType>(&type)) {
      return normalize_function(*function);
    }
    if (const auto *function =
            llvm::dyn_cast<clang::FunctionNoProtoType>(&type)) {
      auto result = normalize_type(function->getReturnType());
      if (!result.has_value()) {
        return std::nullopt;
      }
      return "fn-unspecified()->" + *result;
    }
    if (const auto *record = llvm::dyn_cast<clang::RecordType>(&type)) {
      return normalize_record(*record);
    }
    if (const auto *enumeration = llvm::dyn_cast<clang::EnumType>(&type)) {
      return "enum(" + declaration_anchor(*enumeration->getDecl()) + ")";
    }
    if (const auto *atomic = llvm::dyn_cast<clang::AtomicType>(&type)) {
      return wrap_type("atomic(", atomic->getValueType(), ")");
    }
    if (const auto *complex = llvm::dyn_cast<clang::ComplexType>(&type)) {
      return wrap_type("complex(", complex->getElementType(), ")");
    }
    fail_type(type, type.getTypeClassName());
    return std::nullopt;
  }

  [[nodiscard]] std::optional<std::string>
  normalize_builtin(const clang::BuiltinType &type) {
    using Kind = clang::BuiltinType::Kind;
    switch (type.getKind()) {
    case Kind::Void:
      return "void";
    case Kind::Bool:
      return "bool";
    case Kind::Char_S:
    case Kind::Char_U:
      return "char";
    case Kind::SChar:
      return "i8";
    case Kind::UChar:
    case Kind::Char8:
      return "u8";
    case Kind::Short:
      return "i16";
    case Kind::UShort:
    case Kind::Char16:
      return "u16";
    case Kind::Int:
    case Kind::Long:
    case Kind::WChar_S:
      return "i32";
    case Kind::UInt:
    case Kind::ULong:
    case Kind::WChar_U:
    case Kind::Char32:
      return "u32";
    case Kind::LongLong:
      return "i64";
    case Kind::ULongLong:
      return "u64";
    case Kind::Float:
      return "f32";
    case Kind::Double:
      return "f64";
    case Kind::LongDouble:
      return "f128";
    default:
      fail_type(type, type.getName(context_.getPrintingPolicy()));
      return std::nullopt;
    }
  }

  [[nodiscard]] std::optional<std::string>
  normalize_function(const clang::FunctionProtoType &function) {
    std::string result = "fn(";
    for (unsigned index = 0; index < function.getNumParams(); ++index) {
      if (index != 0U) {
        result.push_back(',');
      }
      auto parameter = normalize_type(function.getParamType(index));
      if (!parameter.has_value()) {
        return std::nullopt;
      }
      result.append(*parameter);
    }
    if (function.isVariadic()) {
      if (function.getNumParams() != 0U) {
        result.push_back(',');
      }
      result.append("...");
    }
    auto returned = normalize_type(function.getReturnType());
    if (!returned.has_value()) {
      return std::nullopt;
    }
    result.append(")->");
    result.append(*returned);
    return result;
  }

  [[nodiscard]] std::optional<std::string>
  normalize_record(const clang::RecordType &record) {
    const clang::RecordDecl &declaration = *record.getDecl();
    std::string result = declaration.isUnion() ? "union(" : "struct(";
    result.append(declaration_anchor(declaration));
    result.push_back(')');
    return result;
  }

  [[nodiscard]] std::optional<std::string> wrap_type(std::string_view prefix,
                                                     clang::QualType inner,
                                                     std::string_view suffix) {
    auto normalized = normalize_type(inner);
    if (!normalized.has_value()) {
      return std::nullopt;
    }
    std::string result(prefix);
    result.append(*normalized);
    result.append(suffix);
    return result;
  }

  [[nodiscard]] std::string
  declaration_anchor(const clang::NamedDecl &declaration) const {
    const std::string name = declaration.getNameAsString();
    if (!name.empty()) {
      return name;
    }
    const clang::SourceLocation location =
        source_manager_.getExpansionLoc(declaration.getLocation());
    if (location.isValid() && source_manager_.isWrittenInMainFile(location)) {
      return "@" + std::to_string(source_manager_.getFileOffset(location));
    }
    return "external-anonymous";
  }

  void fail_type(const clang::Type &type, llvm::StringRef detail) {
    if (!failure_.empty()) {
      return;
    }
    failure_ = "MALBOLGE-FRONTEND-002 unsupported normalized type ";
    failure_.append(detail.str());
    failure_.append(" (clang-class=");
    failure_.append(type.getTypeClassName());
    failure_.push_back(')');
  }

  [[nodiscard]] std::optional<std::string_view>
  declaration_kind(const clang::Decl &declaration) {
    if (llvm::isa<clang::ParmVarDecl>(declaration)) {
      return "parameter-declaration";
    }
    if (llvm::isa<clang::FunctionDecl>(declaration)) {
      return "function-declaration";
    }
    if (llvm::isa<clang::VarDecl>(declaration)) {
      return "variable-declaration";
    }
    if (llvm::isa<clang::FieldDecl>(declaration)) {
      return "field-declaration";
    }
    if (llvm::isa<clang::RecordDecl>(declaration)) {
      return "record-declaration";
    }
    if (llvm::isa<clang::EnumConstantDecl>(declaration)) {
      return "enum-constant-declaration";
    }
    if (llvm::isa<clang::EnumDecl>(declaration)) {
      return "enum-declaration";
    }
    if (llvm::isa<clang::TypedefNameDecl>(declaration)) {
      return "typedef-declaration";
    }
    if (llvm::isa<clang::StaticAssertDecl>(declaration)) {
      return "static-assert-declaration";
    }
    if (llvm::isa<clang::EmptyDecl>(declaration)) {
      return "empty-declaration";
    }
    return std::nullopt;
  }

  [[nodiscard]] std::optional<std::string_view>
  statement_kind(const clang::Stmt &statement) {
    if (llvm::isa<clang::CompoundAssignOperator>(statement)) {
      return "compound-assignment-expression";
    }
    if (llvm::isa<clang::BinaryOperator>(statement)) {
      return "binary-expression";
    }
    if (llvm::isa<clang::UnaryOperator>(statement)) {
      return "unary-expression";
    }
    if (llvm::isa<clang::ImplicitCastExpr>(statement) ||
        llvm::isa<clang::CStyleCastExpr>(statement)) {
      return "cast-expression";
    }
    if (llvm::isa<clang::IntegerLiteral>(statement)) {
      return "integer-literal";
    }
    if (llvm::isa<clang::FloatingLiteral>(statement)) {
      return "floating-literal";
    }
    if (llvm::isa<clang::CharacterLiteral>(statement)) {
      return "character-literal";
    }
    if (llvm::isa<clang::StringLiteral>(statement)) {
      return "string-literal";
    }
    if (llvm::isa<clang::DeclRefExpr>(statement)) {
      return "declaration-reference-expression";
    }
    if (llvm::isa<clang::CallExpr>(statement)) {
      return "call-expression";
    }
    if (llvm::isa<clang::MemberExpr>(statement)) {
      return "member-expression";
    }
    if (llvm::isa<clang::ArraySubscriptExpr>(statement)) {
      return "array-subscript-expression";
    }
    if (llvm::isa<clang::ConditionalOperator>(statement)) {
      return "conditional-expression";
    }
    if (llvm::isa<clang::ConstantExpr>(statement)) {
      return "constant-expression";
    }
    if (llvm::isa<clang::ParenExpr>(statement)) {
      return "parenthesized-expression";
    }
    if (llvm::isa<clang::InitListExpr>(statement)) {
      return "initializer-list-expression";
    }
    if (llvm::isa<clang::DesignatedInitExpr>(statement)) {
      return "designated-initializer-expression";
    }
    if (llvm::isa<clang::CompoundLiteralExpr>(statement)) {
      return "compound-literal-expression";
    }
    if (llvm::isa<clang::UnaryExprOrTypeTraitExpr>(statement)) {
      return "unary-type-trait-expression";
    }
    if (llvm::isa<clang::OffsetOfExpr>(statement)) {
      return "offset-of-expression";
    }
    if (llvm::isa<clang::VAArgExpr>(statement)) {
      return "va-arg-expression";
    }
    if (llvm::isa<clang::GenericSelectionExpr>(statement)) {
      return "generic-selection-expression";
    }
    if (llvm::isa<clang::PredefinedExpr>(statement)) {
      return "predefined-expression";
    }
    if (llvm::isa<clang::AtomicExpr>(statement)) {
      return "atomic-expression";
    }
    if (llvm::isa<clang::ImplicitValueInitExpr>(statement)) {
      return "implicit-value-initializer-expression";
    }
    if (llvm::isa<clang::CompoundStmt>(statement)) {
      return "compound-statement";
    }
    if (llvm::isa<clang::DeclStmt>(statement)) {
      return "declaration-statement";
    }
    if (llvm::isa<clang::ReturnStmt>(statement)) {
      return "return-statement";
    }
    if (llvm::isa<clang::IfStmt>(statement)) {
      return "if-statement";
    }
    if (llvm::isa<clang::WhileStmt>(statement)) {
      return "while-statement";
    }
    if (llvm::isa<clang::DoStmt>(statement)) {
      return "do-statement";
    }
    if (llvm::isa<clang::ForStmt>(statement)) {
      return "for-statement";
    }
    if (llvm::isa<clang::SwitchStmt>(statement)) {
      return "switch-statement";
    }
    if (llvm::isa<clang::CaseStmt>(statement)) {
      return "case-statement";
    }
    if (llvm::isa<clang::DefaultStmt>(statement)) {
      return "default-statement";
    }
    if (llvm::isa<clang::BreakStmt>(statement)) {
      return "break-statement";
    }
    if (llvm::isa<clang::ContinueStmt>(statement)) {
      return "continue-statement";
    }
    if (llvm::isa<clang::GotoStmt>(statement)) {
      return "goto-statement";
    }
    if (llvm::isa<clang::LabelStmt>(statement)) {
      return "label-statement";
    }
    if (llvm::isa<clang::NullStmt>(statement)) {
      return "null-statement";
    }
    return std::nullopt;
  }

  [[nodiscard]] std::optional<std::string>
  storage_class(clang::StorageClass storage) {
    using clang::StorageClass;
    switch (storage) {
    case StorageClass::SC_None:
      return "none";
    case StorageClass::SC_Extern:
      return "extern";
    case StorageClass::SC_Static:
      return "static";
    case StorageClass::SC_Auto:
      return "auto";
    case StorageClass::SC_Register:
      return "register";
    case StorageClass::SC_PrivateExtern:
      failure_ =
          "MALBOLGE-FRONTEND-001 unsupported storage class private-extern";
      return std::nullopt;
    }
    failure_ = "MALBOLGE-FRONTEND-001 unsupported storage class";
    return std::nullopt;
  }

  [[nodiscard]] std::optional<std::string>
  storage_duration(clang::StorageDuration duration) {
    using clang::StorageDuration;
    switch (duration) {
    case StorageDuration::SD_Automatic:
      return "automatic";
    case StorageDuration::SD_Static:
      return "static";
    case StorageDuration::SD_Thread:
      return "thread";
    case StorageDuration::SD_Dynamic:
    case StorageDuration::SD_FullExpression:
      failure_ =
          "MALBOLGE-FRONTEND-001 unsupported declaration storage duration";
      return std::nullopt;
    }
    failure_ = "MALBOLGE-FRONTEND-001 unsupported declaration storage duration";
    return std::nullopt;
  }

  [[nodiscard]] std::optional<std::string> linkage(clang::Linkage value) {
    using clang::Linkage;
    switch (value) {
    case Linkage::None:
    case Linkage::VisibleNone:
      return "none";
    case Linkage::Internal:
      return "internal";
    case Linkage::External:
    case Linkage::UniqueExternal:
      return "external";
    case Linkage::Invalid:
    case Linkage::Module:
      failure_ = "MALBOLGE-FRONTEND-001 unsupported declaration linkage";
      return std::nullopt;
    }
    failure_ = "MALBOLGE-FRONTEND-001 unsupported declaration linkage";
    return std::nullopt;
  }

  [[nodiscard]] static std::string
  variable_definition(clang::VarDecl::DefinitionKind kind) {
    using DefinitionKind = clang::VarDecl::DefinitionKind;
    switch (kind) {
    case DefinitionKind::DeclarationOnly:
      return "declaration";
    case DefinitionKind::TentativeDefinition:
      return "tentative-definition";
    case DefinitionKind::Definition:
      return "definition";
    }
    return "declaration";
  }

  [[nodiscard]] std::optional<std::string>
  enum_underlying_type(const clang::EnumDecl &enumeration) {
    if (enumeration.isFixed()) {
      const clang::QualType integer_type = enumeration.getIntegerType();
      if (integer_type.isNull()) {
        failure_ =
            "MALBOLGE-FRONTEND-002 fixed enum has no underlying integer type";
        return std::nullopt;
      }
      return normalize_type(integer_type);
    }
    if (!enumeration.isCompleteDefinition()) {
      return std::nullopt;
    }
    bool fits_i32 = true;
    bool fits_u32 = true;
    for (const clang::EnumConstantDecl *constant : enumeration.enumerators()) {
      const llvm::APSInt value = constant->getInitVal();
      const bool signed_fit =
          value.isSigned() ? value.isSignedIntN(32U) : value.isIntN(31U);
      const bool unsigned_fit = value.isNonNegative() && value.isIntN(32U);
      fits_i32 = fits_i32 && signed_fit;
      fits_u32 = fits_u32 && unsigned_fit;
    }
    if (fits_i32) {
      return "i32";
    }
    if (fits_u32) {
      return "u32";
    }
    failure_ =
        "MALBOLGE-FRONTEND-002 enum value domain exceeds malbolge-c32-v1";
    return std::nullopt;
  }

  [[nodiscard]] std::optional<bool>
  populate_declaration_semantics(const clang::Decl &declaration, Node &node) {
    if (const auto *variable = llvm::dyn_cast<clang::VarDecl>(&declaration)) {
      node.storage_class = storage_class(variable->getStorageClass());
      node.storage_duration = storage_duration(variable->getStorageDuration());
      node.linkage = linkage(variable->getFormalLinkage());
      if (!node.storage_class.has_value() ||
          !node.storage_duration.has_value() || !node.linkage.has_value()) {
        return std::nullopt;
      }
      if (!llvm::isa<clang::ParmVarDecl>(variable)) {
        node.definition =
            variable_definition(variable->isThisDeclarationADefinition());
      }
      return true;
    }
    if (const auto *function =
            llvm::dyn_cast<clang::FunctionDecl>(&declaration)) {
      node.storage_class = storage_class(function->getStorageClass());
      node.linkage = linkage(function->getFormalLinkage());
      if (!node.storage_class.has_value() || !node.linkage.has_value()) {
        return std::nullopt;
      }
      node.definition = function->isThisDeclarationADefinition()
                            ? "definition"
                            : "declaration";
      node.inline_specified = function->isInlineSpecified();
      return true;
    }
    if (const auto *tag = llvm::dyn_cast<clang::TagDecl>(&declaration)) {
      node.definition =
          tag->isThisDeclarationADefinition() ? "definition" : "declaration";
      if (const auto *enumeration = llvm::dyn_cast<clang::EnumDecl>(tag)) {
        node.enum_fixed = enumeration->isFixed();
        node.enum_underlying = enum_underlying_type(*enumeration);
        if (enumeration->isCompleteDefinition() &&
            !node.enum_underlying.has_value()) {
          return std::nullopt;
        }
      }
    }
    return true;
  }

  [[nodiscard]] std::optional<std::size_t>
  append_declaration(const clang::Decl &declaration) {
    const auto kind = declaration_kind(declaration);
    if (!kind.has_value()) {
      fail_node("declaration", declaration.getDeclKindName(),
                declaration.getLocation());
      return std::nullopt;
    }
    const auto span = make_span(declaration.getSourceRange());
    if (!span.has_value()) {
      fail_node("declaration-location", declaration.getDeclKindName(),
                declaration.getLocation());
      return std::nullopt;
    }
    Node node;
    node.id = nodes_.size() + 1U;
    node.kind = std::string(*kind);
    node.parent = current_parent();
    node.span = *span;
    if (const auto *named = llvm::dyn_cast<clang::NamedDecl>(&declaration)) {
      const std::string name = named->getNameAsString();
      if (!name.empty()) {
        node.name = name;
      }
    }
    if (const auto *value = llvm::dyn_cast<clang::ValueDecl>(&declaration)) {
      node.type = normalize_type(value->getType());
      if (!node.type.has_value()) {
        return std::nullopt;
      }
    } else if (const auto *alias =
                   llvm::dyn_cast<clang::TypedefNameDecl>(&declaration)) {
      node.type = normalize_type(alias->getUnderlyingType());
      if (!node.type.has_value()) {
        return std::nullopt;
      }
    } else if (const auto *record =
                   llvm::dyn_cast<clang::RecordDecl>(&declaration)) {
      node.type = normalize_type(context_.getCanonicalTagType(record));
      node.operation = record->isUnion() ? "union" : "struct";
      if (!node.type.has_value()) {
        return std::nullopt;
      }
    } else if (const auto *enumeration =
                   llvm::dyn_cast<clang::EnumDecl>(&declaration)) {
      node.type = normalize_type(context_.getCanonicalTagType(enumeration));
      if (!node.type.has_value()) {
        return std::nullopt;
      }
    }
    if (const auto *enumerator =
            llvm::dyn_cast<clang::EnumConstantDecl>(&declaration)) {
      node.constant_integer = apsint_text(enumerator->getInitVal());
    }
    if (!populate_declaration_semantics(declaration, node).has_value()) {
      return std::nullopt;
    }
    const std::size_t id = node.id;
    nodes_.push_back(std::move(node));
    return id;
  }

  [[nodiscard]] std::optional<std::size_t>
  append_statement(const clang::Stmt &statement) {
    const auto kind = statement_kind(statement);
    if (!kind.has_value()) {
      fail_node("statement", statement.getStmtClassName(),
                statement.getBeginLoc());
      return std::nullopt;
    }
    const auto span = make_span(statement.getSourceRange());
    if (!span.has_value()) {
      fail_node("statement-location", statement.getStmtClassName(),
                statement.getBeginLoc());
      return std::nullopt;
    }
    Node node;
    node.id = nodes_.size() + 1U;
    node.kind = std::string(*kind);
    node.parent = current_parent();
    node.span = *span;
    if (const auto *expression = llvm::dyn_cast<clang::Expr>(&statement)) {
      node.type = normalize_type(expression->getType());
      if (!node.type.has_value()) {
        return std::nullopt;
      }
      if (auto constant = expression->getIntegerConstantExpr(context_)) {
        node.constant_integer = apsint_text(*constant);
      }
    }
    populate_statement_details(statement, node);
    if (!failure_.empty()) {
      return std::nullopt;
    }
    const std::size_t id = node.id;
    nodes_.push_back(std::move(node));
    return id;
  }

  void populate_statement_details(const clang::Stmt &statement, Node &node) {
    if (const auto *binary =
            llvm::dyn_cast<clang::BinaryOperator>(&statement)) {
      node.operation = binary->getOpcodeStr().str();
    } else if (const auto *unary =
                   llvm::dyn_cast<clang::UnaryOperator>(&statement)) {
      node.operation =
          clang::UnaryOperator::getOpcodeStr(unary->getOpcode()).str();
    } else if (const auto *cast = llvm::dyn_cast<clang::CastExpr>(&statement)) {
      node.operation = cast_operation(cast->getCastKind());
      if (!node.operation.has_value()) {
        fail_node("cast", cast->getCastKindName(), cast->getBeginLoc());
      }
    } else if (const auto *trait =
                   llvm::dyn_cast<clang::UnaryExprOrTypeTraitExpr>(
                       &statement)) {
      node.operation = clang::getTraitSpelling(trait->getKind());
    }
    populate_reference(statement, node);
    populate_literal(statement, node);
  }

  void populate_reference(const clang::Stmt &statement, Node &node) const {
    if (const auto *reference =
            llvm::dyn_cast<clang::DeclRefExpr>(&statement)) {
      node.reference = declaration_reference(*reference->getDecl());
      return;
    }
    if (const auto *member = llvm::dyn_cast<clang::MemberExpr>(&statement)) {
      node.reference = declaration_reference(*member->getMemberDecl());
      return;
    }
    if (const auto *call = llvm::dyn_cast<clang::CallExpr>(&statement)) {
      if (const clang::FunctionDecl *callee = call->getDirectCallee()) {
        node.reference = declaration_reference(*callee);
      }
      return;
    }
    if (const auto *label = llvm::dyn_cast<clang::LabelStmt>(&statement)) {
      node.name = label->getName();
      return;
    }
    if (const auto *jump = llvm::dyn_cast<clang::GotoStmt>(&statement)) {
      node.reference = jump->getLabel()->getNameAsString();
    }
  }

  void populate_literal(const clang::Stmt &statement, Node &node) const {
    if (const auto *integer =
            llvm::dyn_cast<clang::IntegerLiteral>(&statement)) {
      const bool is_unsigned = integer->getType()->isUnsignedIntegerType();
      node.literal =
          apsint_text(llvm::APSInt(integer->getValue(), is_unsigned));
      return;
    }
    if (const auto *floating =
            llvm::dyn_cast<clang::FloatingLiteral>(&statement)) {
      node.literal = "0x" + apint_hex(floating->getValue().bitcastToAPInt());
      return;
    }
    if (const auto *character =
            llvm::dyn_cast<clang::CharacterLiteral>(&statement)) {
      node.literal = std::to_string(character->getValue());
      return;
    }
    if (const auto *string = llvm::dyn_cast<clang::StringLiteral>(&statement)) {
      const llvm::StringRef bytes = string->getBytes();
      const auto *data = reinterpret_cast<const std::uint8_t *>(bytes.data());
      node.literal =
          hex_bytes(llvm::ArrayRef<std::uint8_t>(data, bytes.size()));
    }
  }

  [[nodiscard]] std::string
  declaration_reference(const clang::NamedDecl &declaration) const {
    const clang::Decl *canonical = declaration.getCanonicalDecl();
    const auto *named = llvm::dyn_cast<clang::NamedDecl>(canonical);
    const clang::NamedDecl &selected = named == nullptr ? declaration : *named;
    const std::string name = selected.getNameAsString();
    const clang::SourceLocation location =
        source_manager_.getExpansionLoc(selected.getLocation());
    if (location.isValid() && source_manager_.isWrittenInMainFile(location)) {
      return name + "@" +
             std::to_string(source_manager_.getFileOffset(location));
    }
    return "external:" + (name.empty() ? std::string("anonymous") : name);
  }

  [[nodiscard]] std::optional<std::string>
  unary_type_trait_operation(clang::UnaryExprOrTypeTrait kind) const {
    using clang::UnaryExprOrTypeTrait;
    switch (kind) {
    case UnaryExprOrTypeTrait::UETT_AlignOf:
      return "alignof";
    case UnaryExprOrTypeTrait::UETT_SizeOf:
      return "sizeof";
    default:
      return std::nullopt;
    }
  }

  [[nodiscard]] std::optional<std::string>
  cast_operation(clang::CastKind kind) const {
    using clang::CastKind;
    switch (kind) {
    case CastKind::CK_ArrayToPointerDecay:
      return "array-to-pointer";
    case CastKind::CK_AtomicToNonAtomic:
      return "atomic-to-value";
    case CastKind::CK_BitCast:
      return "bit-cast";
    case CastKind::CK_BooleanToSignedIntegral:
      return "bool-to-signed";
    case CastKind::CK_FloatingCast:
      return "floating-cast";
    case CastKind::CK_FloatingComplexCast:
      return "floating-complex-cast";
    case CastKind::CK_FloatingComplexToBoolean:
      return "floating-complex-to-bool";
    case CastKind::CK_FloatingComplexToIntegralComplex:
      return "floating-complex-to-integral-complex";
    case CastKind::CK_FloatingComplexToReal:
      return "floating-complex-to-real";
    case CastKind::CK_FloatingRealToComplex:
      return "floating-real-to-complex";
    case CastKind::CK_FloatingToBoolean:
      return "floating-to-bool";
    case CastKind::CK_FloatingToIntegral:
      return "floating-to-integral";
    case CastKind::CK_FunctionToPointerDecay:
      return "function-to-pointer";
    case CastKind::CK_IntegralCast:
      return "integral-cast";
    case CastKind::CK_IntegralComplexCast:
      return "integral-complex-cast";
    case CastKind::CK_IntegralComplexToBoolean:
      return "integral-complex-to-bool";
    case CastKind::CK_IntegralComplexToFloatingComplex:
      return "integral-complex-to-floating-complex";
    case CastKind::CK_IntegralComplexToReal:
      return "integral-complex-to-real";
    case CastKind::CK_IntegralRealToComplex:
      return "integral-real-to-complex";
    case CastKind::CK_IntegralToBoolean:
      return "integral-to-bool";
    case CastKind::CK_IntegralToFloating:
      return "integral-to-floating";
    case CastKind::CK_IntegralToPointer:
      return "integral-to-pointer";
    case CastKind::CK_LValueToRValue:
      return "lvalue-to-rvalue";
    case CastKind::CK_NoOp:
      return "no-op";
    case CastKind::CK_NonAtomicToAtomic:
      return "value-to-atomic";
    case CastKind::CK_NullToPointer:
      return "null-to-pointer";
    case CastKind::CK_PointerToBoolean:
      return "pointer-to-bool";
    case CastKind::CK_PointerToIntegral:
      return "pointer-to-integral";
    case CastKind::CK_ToVoid:
      return "to-void";
    default:
      return std::nullopt;
    }
  }

  [[nodiscard]] std::optional<Span>
  make_span(clang::SourceRange source_range) const {
    clang::SourceLocation begin =
        source_manager_.getExpansionLoc(source_range.getBegin());
    clang::SourceLocation end =
        source_manager_.getExpansionLoc(source_range.getEnd());
    if (!begin.isValid() || !end.isValid() ||
        !source_manager_.isWrittenInMainFile(begin) ||
        !source_manager_.isWrittenInMainFile(end)) {
      return std::nullopt;
    }
    const clang::SourceLocation token_end = clang::Lexer::getLocForEndOfToken(
        end, 0U, source_manager_, context_.getLangOpts());
    if (token_end.isValid() && source_manager_.isWrittenInMainFile(token_end)) {
      end = token_end;
    }
    return Span{make_position(begin), make_position(end)};
  }

  [[nodiscard]] Position make_position(clang::SourceLocation location) const {
    const clang::SourceLocation expanded =
        source_manager_.getExpansionLoc(location);
    return Position{
        source_manager_.getFileOffset(expanded),
        source_manager_.getExpansionColumnNumber(expanded),
        source_manager_.getExpansionLineNumber(expanded),
    };
  }

  [[nodiscard]] bool should_record(clang::SourceLocation location) const {
    if (!location.isValid()) {
      return false;
    }
    const clang::SourceLocation expanded =
        source_manager_.getExpansionLoc(location);
    return expanded.isValid() && source_manager_.isWrittenInMainFile(expanded);
  }

  [[nodiscard]] std::size_t current_parent() const {
    return parents_.empty() ? 0U : parents_.back();
  }

  void fail_node(std::string_view category, llvm::StringRef detail,
                 clang::SourceLocation location) {
    if (!failure_.empty()) {
      return;
    }
    failure_ = "MALBOLGE-FRONTEND-001 unsupported ";
    failure_.append(category);
    failure_.push_back(' ');
    failure_.append(detail.str());
    if (location.isValid()) {
      const clang::SourceLocation expanded =
          source_manager_.getExpansionLoc(location);
      if (expanded.isValid() && source_manager_.isWrittenInMainFile(expanded)) {
        failure_.append(" at ");
        failure_.append(
            std::to_string(source_manager_.getExpansionLineNumber(expanded)));
        failure_.push_back(':');
        failure_.append(
            std::to_string(source_manager_.getExpansionColumnNumber(expanded)));
      }
    }
  }

  clang::ASTContext &context_;
  std::string failure_;
  std::vector<Node> nodes_;
  std::vector<std::size_t> parents_;
  clang::SourceManager &source_manager_;
};

void emit_position(llvm::json::OStream &json, const Position &position) {
  json.object([&] {
    json.attribute("byte", static_cast<std::int64_t>(position.byte));
    json.attribute("line", static_cast<std::int64_t>(position.line));
    json.attribute("column", static_cast<std::int64_t>(position.column));
  });
}

void emit_span(llvm::json::OStream &json, const Span &span) {
  json.object([&] {
    json.attributeBegin("begin");
    emit_position(json, span.begin);
    json.attributeEnd();
    json.attributeBegin("end");
    emit_position(json, span.end);
    json.attributeEnd();
  });
}

void emit_node(llvm::json::OStream &json, const Node &node) {
  json.object([&] {
    json.attribute("id", static_cast<std::int64_t>(node.id));
    json.attribute("parent", static_cast<std::int64_t>(node.parent));
    json.attribute("kind", node.kind);
    json.attributeBegin("span");
    emit_span(json, node.span);
    json.attributeEnd();
    if (node.name.has_value()) {
      json.attribute("name", *node.name);
    }
    if (node.type.has_value()) {
      json.attribute("type", *node.type);
    }
    if (node.operation.has_value()) {
      json.attribute("operation", *node.operation);
    }
    if (node.reference.has_value()) {
      json.attribute("reference", *node.reference);
    }
    if (node.constant_integer.has_value()) {
      json.attribute("constant_integer", *node.constant_integer);
    }
    if (node.definition.has_value()) {
      json.attribute("definition", *node.definition);
    }
    if (node.enum_fixed.has_value()) {
      json.attribute("enum_fixed", *node.enum_fixed);
    }
    if (node.enum_underlying.has_value()) {
      json.attribute("enum_underlying", *node.enum_underlying);
    }
    if (node.inline_specified.has_value()) {
      json.attribute("inline_specified", *node.inline_specified);
    }
    if (node.linkage.has_value()) {
      json.attribute("linkage", *node.linkage);
    }
    if (node.storage_class.has_value()) {
      json.attribute("storage_class", *node.storage_class);
    }
    if (node.storage_duration.has_value()) {
      json.attribute("storage_duration", *node.storage_duration);
    }
    if (node.literal.has_value()) {
      json.attribute("literal", *node.literal);
    }
  });
}

[[nodiscard]] std::string serialize_artifact(const FrontendRequest &request,
                                             const std::vector<Node> &nodes) {
  std::string output;
  llvm::raw_string_ostream stream(output);
  llvm::json::OStream json(stream, 2U);
  json.object([&] {
    json.attribute("schema_version", 1);
    json.attribute("artifact_id", kArtifactId);
    json.attributeObject("clang", [&] {
      json.attribute("version", kClangVersion);
      json.attribute("target", kClangTarget);
      json.attribute("language", kLanguage);
    });
    json.attributeObject("profile", [&] {
      json.attribute("abi_id", kAbiId);
      json.attribute("target_profile", kTargetProfile);
    });
    json.attributeObject("source", [&] {
      json.attribute("id", request.source_id);
      json.attribute("sha256", source_sha256(request.source_text));
    });
    json.attributeArray("nodes", [&] {
      for (const Node &node : nodes) {
        emit_node(json, node);
      }
    });
  });
  json.flush();
  return output;
}

class NormalizeConsumer final : public clang::ASTConsumer {
public:
  NormalizeConsumer(const FrontendRequest &request, FrontendResult &result)
      : request_(request), result_(result) {}

  void HandleTranslationUnit(clang::ASTContext &context) override {
    Normalizer normalizer(context);
    if (!normalizer.TraverseDecl(context.getTranslationUnitDecl())) {
      result_.diagnostic = normalizer.failure();
      result_.status = 4;
      return;
    }
    result_.artifact = serialize_artifact(request_, normalizer.nodes());
    result_.status = 0;
  }

private:
  const FrontendRequest &request_;
  FrontendResult &result_;
};

class NormalizeAction final : public clang::ASTFrontendAction {
public:
  NormalizeAction(const FrontendRequest &request, FrontendResult &result)
      : request_(request), result_(result) {}

  std::unique_ptr<clang::ASTConsumer>
  CreateASTConsumer(clang::CompilerInstance &, llvm::StringRef) override {
    return std::make_unique<NormalizeConsumer>(request_, result_);
  }

private:
  const FrontendRequest &request_;
  FrontendResult &result_;
};

[[nodiscard]] bool portable_source_id(std::string_view value) {
  if (value.empty() || value.front() == '/' || value.back() == '/' ||
      value.find(static_cast<char>(92)) != std::string_view::npos ||
      value.find(':') != std::string_view::npos) {
    return false;
  }
  std::size_t begin = 0U;
  while (begin < value.size()) {
    const std::size_t end = value.find('/', begin);
    const std::string_view segment =
        value.substr(begin, end == std::string_view::npos ? value.size() - begin
                                                          : end - begin);
    if (segment.empty() || segment == "." || segment == "..") {
      return false;
    }
    for (const unsigned char byte : segment) {
      const bool allowed = (byte >= 'a' && byte <= 'z') ||
                           (byte >= 'A' && byte <= 'Z') ||
                           (byte >= '0' && byte <= '9') || byte == '.' ||
                           byte == '_' || byte == '-';
      if (!allowed) {
        return false;
      }
    }
    if (end == std::string_view::npos) {
      break;
    }
    begin = end + 1U;
  }
  return true;
}

[[nodiscard]] std::vector<std::string>
frontend_arguments(const FrontendRequest &request) {
  return {
      "--target=wasm32-unknown-unknown",
      "-std=c23",
      "-ffreestanding",
      "-fno-builtin",
      "-pedantic-errors",
      "-Werror=implicit-function-declaration",
      "-Werror=incompatible-pointer-types",
      "-Werror=int-conversion",
      "-Werror=return-type",
      "-Werror=uninitialized",
      "-fno-color-diagnostics",
      "-nostdinc",
      "-isystem",
      request.resource_dir + "/include",
      "-I" + request.guest_include,
      "-x",
      "c",
  };
}

} // namespace

FrontendResult normalize_c_source(const FrontendRequest &request) {
  FrontendResult result;
  if (!portable_source_id(request.source_id) || request.resource_dir.empty() ||
      request.guest_include.empty()) {
    result.diagnostic = "MALBOLGE-FRONTEND-003 invalid frontend request";
    result.status = 2;
    return result;
  }
  const bool executed = clang::tooling::runToolOnCodeWithArgs(
      std::make_unique<NormalizeAction>(request, result), request.source_text,
      frontend_arguments(request), request.source_id, "malbolge-c-frontend");
  if (!executed) {
    result.artifact.clear();
    if (result.diagnostic.empty()) {
      result.diagnostic =
          "MALBOLGE-FRONTEND-004 Clang parse failed for " + request.source_id;
      result.status = 3;
    }
  }
  return result;
}

} // namespace malbolge::compiler::c_frontend
