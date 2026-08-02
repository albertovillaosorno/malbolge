@echo off
setlocal
set "ROOT=%~dp0.."
set "TARGET=%ROOT%\.cache\rust\target\release\malbolge.exe"
set "OUTPUT=%~dp0bin\malbolge.exe"
if defined MALBOLGE_CARGO (
  set "CARGO=%MALBOLGE_CARGO%"
) else (
  for %%I in (cargo.exe) do set "CARGO=%%~$PATH:I"
)
if not defined CARGO (
  echo malbolge: cargo.exe was not found. Install Rust 1.97.1 or set ^
MALBOLGE_CARGO. 1>&2
  exit /b 1
)
if not exist "%~dp0bin" mkdir "%~dp0bin"
pushd "%ROOT%"
"%CARGO%" build --release --bin malbolge
set "RESULT=%ERRORLEVEL%"
popd
if not "%RESULT%"=="0" exit /b %RESULT%
copy /Y "%TARGET%" "%OUTPUT%" >nul
exit /b %ERRORLEVEL%
