@echo off
setlocal
set "CLI_DIR=%~dp0"
set "MALBOLGE_ROOT=%CLI_DIR%.."
set "MALBOLGE_BIN=%CLI_DIR%bin\malbolge.exe"
if not exist "%MALBOLGE_BIN%" (
  echo malbolge: CLI binary is not built. Run cli\build-windows.cmd first. 1>&2
  exit /b 1
)
"%MALBOLGE_BIN%" %*
exit /b %ERRORLEVEL%
