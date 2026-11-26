# Rebuild (no retranslation) and run the port for a few seconds; print the interesting log lines.
param([int]$Seconds = 25, [switch]$NoBuild)
$tools = $PSScriptRoot
if (-not $NoBuild) {
    pwsh -NoProfile -File (Join-Path $tools 'build.ps1') -SkipTranslate *> (Join-Path $tools '..\pipeline.log')
    if ($LASTEXITCODE) { Get-Content (Join-Path $tools '..\pipeline.log') -Tail 5; exit 1 }
}
$exeDir = Join-Path $tools '..\Wiicompiled\build\lifeking-native' | Resolve-Path
$out = Join-Path $tools '..\run.out'; $err = Join-Path $tools '..\run.err'
$p = Start-Process -FilePath (Join-Path $exeDir 'WiiCompiled.exe') -WorkingDirectory $exeDir -PassThru `
    -RedirectStandardOutput $out -RedirectStandardError $err
$deadline = (Get-Date).AddSeconds($Seconds)
while (-not $p.HasExited -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; "still running after $Seconds s (killed)" } else { "exited $($p.ExitCode)" }
Get-Content $err, $out | Where-Object { $_ -notmatch '^\[aurora\]|Loaded _|^  [A-Za-z]' } | Select-Object -Last 25
