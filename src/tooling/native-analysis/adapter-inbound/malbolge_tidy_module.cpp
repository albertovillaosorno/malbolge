// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Clang AST adapter checks for the deterministic Malbolge guest-C profile.
// - Must-Not:
//   - Fork Clang, weaken baseline checks, or own compiler lowering policy.
// - Allows:
//   - Inputs: pinned Clang AST nodes supplied by clang-tidy.
//   - Outputs: documented source-located malbolge-* diagnostics.
//   - Side effects: registration with the selected clang-tidy host at load.
// - Split-When:
//   - Split when a check family gains independent profile or release ownership.
// - Merge-When:
//   - Merge when source ABI preflight migrates wholly into this adapter.
// - Summary:
//   - Register deterministic guest-C checks in the pinned clang-tidy host.
// - Description:
//   - Bridges an out-of-tree module into the host registry without a fork.
// - Usage:
//   - Loaded explicitly with --load by manual guest-C validation.
// - Defaults:
//   - Incompatible host registration leaves validation unavailable.
//

//! Clang AST checks for the deterministic Malbolge guest-C ABI.

#include "clang-tidy/ClangTidyCheck.h"
#include "clang-tidy/ClangTidyModule.h"
#include "clang/AST/Attr.h"
#include "clang/AST/Decl.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"

#ifdef _WIN32
#include <windows.h>
#endif

#include <memory>
#include <string>

namespace malbolge::tidy {
namespace {

using Registry = clang::tidy::ClangTidyModuleRegistry;
using clang::Decl;
using clang::FieldDecl;
using clang::NamedDecl;
using clang::QualType;
using clang::RecordDecl;
using clang::TypedefNameDecl;
using clang::TypedefType;
using clang::ValueDecl;
using clang::ast_matchers::MatchFinder;
using namespace clang::ast_matchers;

constexpr unsigned kMaxAlignmentBytes = 16;

clang::SourceLocation attributeLocation(const Decl &Declaration,
                                        const clang::Attr *Attribute) {
  if (Attribute != nullptr && Attribute->getLocation().isValid())
    return Attribute->getLocation();
  return Declaration.getLocation();
}

class AbiBitFieldCheck final : public clang::tidy::ClangTidyCheck {
public:
  AbiBitFieldCheck(llvm::StringRef Name, clang::tidy::ClangTidyContext *Context)
      : ClangTidyCheck(Name, Context) {}

  void registerMatchers(MatchFinder *Finder) override {
    Finder->addMatcher(
        fieldDecl(isExpansionInMainFile(), isBitField()).bind("bit-field"),
        this);
  }

  void check(const MatchFinder::MatchResult &Result) override {
    const auto *Field = Result.Nodes.getNodeAs<FieldDecl>("bit-field");
    if (Field == nullptr)
      return;
    diag(Field->getLocation(),
         "MALBOLGE-ABI-001 bit-fields are outside malbolge-c32-v1 "
         "object layout");
  }
};

class AbiPackedLayoutCheck final : public clang::tidy::ClangTidyCheck {
public:
  AbiPackedLayoutCheck(llvm::StringRef Name,
                       clang::tidy::ClangTidyContext *Context)
      : ClangTidyCheck(Name, Context) {}

  void registerMatchers(MatchFinder *Finder) override {
    Finder->addMatcher(
        decl(isExpansionInMainFile(), hasAttr(clang::attr::Packed))
            .bind("packed-decl"),
        this);
  }

  void check(const MatchFinder::MatchResult &Result) override {
    const auto *Declaration = Result.Nodes.getNodeAs<Decl>("packed-decl");
    if (Declaration == nullptr)
      return;
    diag(attributeLocation(*Declaration,
                           Declaration->getAttr<clang::PackedAttr>()),
         "MALBOLGE-ABI-002 packed layout is outside malbolge-c32-v1");
  }
};

class AbiPragmaPackCheck final : public clang::tidy::ClangTidyCheck {
public:
  AbiPragmaPackCheck(llvm::StringRef Name,
                     clang::tidy::ClangTidyContext *Context)
      : ClangTidyCheck(Name, Context) {}

  void registerMatchers(MatchFinder *Finder) override {
    Finder->addMatcher(recordDecl(isExpansionInMainFile(),
                                  hasAttr(clang::attr::MaxFieldAlignment))
                           .bind("pragma-packed-record"),
                       this);
  }

  void check(const MatchFinder::MatchResult &Result) override {
    const auto *Record =
        Result.Nodes.getNodeAs<RecordDecl>("pragma-packed-record");
    if (Record == nullptr)
      return;
    const auto *Attribute = Record->getAttr<clang::MaxFieldAlignmentAttr>();
    diag(attributeLocation(*Record, Attribute),
         "MALBOLGE-ABI-003 #pragma pack is outside malbolge-c32-v1");
  }
};

class AbiOverAlignmentCheck final : public clang::tidy::ClangTidyCheck {
public:
  AbiOverAlignmentCheck(llvm::StringRef Name,
                        clang::tidy::ClangTidyContext *Context)
      : ClangTidyCheck(Name, Context) {}

  void registerMatchers(MatchFinder *Finder) override {
    Finder->addMatcher(decl(isExpansionInMainFile(), unless(isImplicit()),
                            hasAttr(clang::attr::Aligned))
                           .bind("aligned-decl"),
                       this);
  }

  void check(const MatchFinder::MatchResult &Result) override {
    const auto *Declaration = Result.Nodes.getNodeAs<Decl>("aligned-decl");
    if (Declaration == nullptr || Result.Context == nullptr)
      return;
    const unsigned CharWidth = Result.Context->getCharWidth();
    const unsigned AlignmentBits = Declaration->getMaxAlignment();
    const unsigned MaximumBits = kMaxAlignmentBytes * CharWidth;
    if (AlignmentBits <= MaximumBits)
      return;
    const unsigned AlignmentBytes = AlignmentBits / CharWidth;
    const auto *Attribute = Declaration->getAttr<clang::AlignedAttr>();
    diag(attributeLocation(*Declaration, Attribute),
         "MALBOLGE-ABI-004 requested alignment %0 exceeds "
         "malbolge-c32-v1 maximum %1")
        << AlignmentBytes << kMaxAlignmentBytes;
  }
};

struct TypeDiagnostic final {
  const char *Code;
  const char *Message;
};

const TypeDiagnostic *forbiddenTypeDiagnostic(llvm::StringRef TypeText) {
  static constexpr TypeDiagnostic BitInt = {
      "MALBOLGE-ABI-005", "bit-precise integers are outside malbolge-c32-v1"};
  static constexpr TypeDiagnostic Int128 = {
      "MALBOLGE-ABI-006",
      "128-bit integer extensions are outside malbolge-c32-v1"};
  static constexpr TypeDiagnostic Vector = {
      "MALBOLGE-ABI-007", "compiler vector types are outside malbolge-c32-v1"};
  static constexpr TypeDiagnostic AddressSpace = {
      "MALBOLGE-ABI-008",
      "non-default address spaces are outside malbolge-c32-v1"};

  if (TypeText.contains("_BitInt("))
    return &BitInt;
  if (TypeText.contains("__int128"))
    return &Int128;
  if (TypeText.contains("__vector_size__") ||
      TypeText.contains("ext_vector_type"))
    return &Vector;
  if (TypeText.contains("address_space("))
    return &AddressSpace;
  return nullptr;
}

bool isMainFileTypedefSpelling(QualType Type,
                               const clang::SourceManager &Sources) {
  const auto *Alias =
      llvm::dyn_cast_or_null<TypedefType>(Type.getTypePtrOrNull());
  if (Alias == nullptr)
    return false;
  return Sources.isWrittenInMainFile(Alias->getDecl()->getLocation());
}

class AbiTypeSurfaceCheck final : public clang::tidy::ClangTidyCheck {
public:
  AbiTypeSurfaceCheck(llvm::StringRef Name,
                      clang::tidy::ClangTidyContext *Context)
      : ClangTidyCheck(Name, Context) {}

  void registerMatchers(MatchFinder *Finder) override {
    Finder->addMatcher(valueDecl(isExpansionInMainFile(), unless(isImplicit()))
                           .bind("typed-value"),
                       this);
    Finder->addMatcher(
        typedefNameDecl(isExpansionInMainFile(), unless(isImplicit()))
            .bind("typed-alias"),
        this);
  }

  void check(const MatchFinder::MatchResult &Result) override {
    const NamedDecl *Declaration = nullptr;
    QualType Type;
    if (const auto *Alias =
            Result.Nodes.getNodeAs<TypedefNameDecl>("typed-alias")) {
      Declaration = Alias;
      Type = Alias->getUnderlyingType();
    } else if (const auto *Value =
                   Result.Nodes.getNodeAs<ValueDecl>("typed-value")) {
      if (Result.SourceManager != nullptr &&
          isMainFileTypedefSpelling(Value->getType(), *Result.SourceManager))
        return;
      Declaration = Value;
      Type = Value->getType();
    }
    if (Declaration == nullptr || Type.isNull())
      return;

    const std::string TypeText = Type.getCanonicalType().getAsString();
    const TypeDiagnostic *Diagnostic = forbiddenTypeDiagnostic(TypeText);
    if (Diagnostic == nullptr)
      return;
    const std::string Message =
        std::string(Diagnostic->Code) + " " + Diagnostic->Message;
    diag(Declaration->getLocation(), Message);
  }
};

class MalbolgeTidyModule final : public clang::tidy::ClangTidyModule {
public:
  void
  addCheckFactories(clang::tidy::ClangTidyCheckFactories &Factories) override {
    Factories.registerCheck<AbiBitFieldCheck>("malbolge-abi-bit-field");
    Factories.registerCheck<AbiPackedLayoutCheck>("malbolge-abi-packed-layout");
    Factories.registerCheck<AbiPragmaPackCheck>("malbolge-abi-pragma-pack");
    Factories.registerCheck<AbiOverAlignmentCheck>(
        "malbolge-abi-over-alignment");
    Factories.registerCheck<AbiTypeSurfaceCheck>("malbolge-abi-type-surface");
  }
};

#ifdef _WIN32
std::unique_ptr<clang::tidy::ClangTidyModule> createModule() {
  return std::make_unique<MalbolgeTidyModule>();
}

Registry::entry
    ModuleEntry("malbolge-module",
                "Adds deterministic Malbolge guest-C compatibility checks.",
                &createModule);
Registry::node ModuleNode(ModuleEntry);

class ModuleRegistration final {
public:
  ModuleRegistration() {
    HMODULE Host = GetModuleHandleW(nullptr);
    if (Host == nullptr)
      return;
    using RegisterNode = void(__cdecl *)(Registry::node *);
    auto Register = reinterpret_cast<RegisterNode>(
        GetProcAddress(Host, "malbolge_tidy_register_node"));
    if (Register != nullptr)
      Register(&ModuleNode);
  }
};

ModuleRegistration Registration;
#else
Registry::Add<MalbolgeTidyModule> ModuleRegistration(
    "malbolge-module",
    "Adds deterministic Malbolge guest-C compatibility checks.");
[[maybe_unused]] volatile int MalbolgeTidyModuleAnchorSource = 0;
#endif

} // namespace
} // namespace malbolge::tidy
