param(
    [string]$Destination = ""
)
$ErrorActionPreference = "Stop"
$cli = (Resolve-Path (Join-Path $PSScriptRoot ".")).Path
$pathEntries = $env:PATH -split ";" | Where-Object { $_ }
function Test-PathEntry([string]$Candidate) {
    $resolved = [IO.Path]::GetFullPath($Candidate)
    return [bool]($pathEntries | Where-Object {
        [string]::Equals(
            [IO.Path]::GetFullPath($_),
            $resolved,
            [StringComparison]::OrdinalIgnoreCase
        )
    })
}
if (-not $Destination) {
    $preferred = "$env:USERPROFILE\bin"
    $windowsApps = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
    if ((Test-Path $preferred) -and (Test-PathEntry $preferred)) {
        $Destination = $preferred
    }
    elseif ((Test-Path $windowsApps) -and (Test-PathEntry $windowsApps)) {
        $Destination = $windowsApps
    }
    else {
        # jig-ignore-next-line: indivisible reviewed identifier
        throw "No writable standard user directory already present in PATH was found."
    }
}
$resolvedDestination = [IO.Path]::GetFullPath($Destination)
if (-not (Test-PathEntry $resolvedDestination)) {
    throw "Destination is not already in PATH: $resolvedDestination"
}
New-Item -ItemType Directory -Force $resolvedDestination | Out-Null
$cmdTarget = Join-Path $resolvedDestination "malbolge.cmd"
$cmd = "@call `"$(Join-Path $cli 'malbolge.cmd')`" %*`r`n"
[IO.File]::WriteAllText($cmdTarget, $cmd, [Text.Encoding]::ASCII)
$drive = $cli.Substring(0, 1).ToLowerInvariant()
$rest = $cli.Substring(2).Replace("\", "/")
$bashCli = "/$drive$rest/malbolge"
$bashTarget = Join-Path $resolvedDestination "malbolge"
$bash = "#!/usr/bin/env bash`nexec `"$bashCli`" `"`$@`"`n"
[IO.File]::WriteAllText($bashTarget, $bash, [Text.UTF8Encoding]::new($false))
Write-Host "Installed malbolge shims in $resolvedDestination"
Write-Host "PowerShell/cmd: malbolge <path>"
Write-Host "Git Bash:       malbolge <path>"
