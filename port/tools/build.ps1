# Full local pipeline for the My Life as a King port (WiiCompiled branch `lifeking`).
# Usage: pwsh port/lk-tools/build.ps1 [-SkipTranslate]
param([switch]$SkipTranslate)
$ErrorActionPreference = 'Stop'
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$tools = $PSScriptRoot
$wc = Join-Path $tools '..\Wiicompiled' | Resolve-Path
$symbols = Join-Path $tools '..\..\KingLifePC\config\WFCPGD\symbols.txt' | Resolve-Path

python -I (Join-Path $tools 'make_layer.py') --wiicompiled $wc --symbols $symbols
if ($LASTEXITCODE) { throw 'make_layer failed' }

Push-Location $wc
try {
    $t = 'translator/src/Translator.Cli/bin/Release/net8.0/Translator.Cli.dll'
    $p = 'projects/lifeking/recomp.yml'
    dotnet build translator/src/Translator.Cli/Translator.Cli.csproj -c Release -v q | Out-Null
    if ($LASTEXITCODE) { throw 'translator build failed' }
    if (-not $SkipTranslate) {
        dotnet $t translate-recursive 0x8000403C --project $p --output-metadata generated/base_translation_output.json *> ..\translate.log
        if ($LASTEXITCODE) { throw 'translate failed (see port/translate.log)' }
        dotnet $t generate-data-init --project $p *> ..\datainit.log
        if ($LASTEXITCODE) { throw 'data init failed' }
    }
    dotnet $t emit-native-index --project $p --out projects/lifeking/native-index.json *> $null
    dotnet $t emit-build-shards --project $p --base-metadata generated/base_translation_output.json `
        --base-functions-dir generated/functions --native-source-dir projects/lifeking/native `
        --native-index projects/lifeking/native-index.json *> ..\shards.log
    if ($LASTEXITCODE) { throw 'emit-build-shards failed (see port/shards.log)' }
    if (-not (Test-Path build/lifeking-native/build.ninja)) {
        $ninja = (Get-Command ninja).Source
        cmake -S runtime -B build/lifeking-native -G Ninja -DCMAKE_MAKE_PROGRAM="$ninja" `
            -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_BUILD_TYPE=Release *> ..\cmake.log
        if ($LASTEXITCODE) { throw 'cmake failed (see port/cmake.log)' }
    }
    ninja -C build/lifeking-native WiiCompiled *> ..\build.log
    if ($LASTEXITCODE) { throw 'ninja failed (see port/build.log)' }
    # The exe is KingLife.exe since v0.2; drop the pre-0.2 name so nothing starts a stale build.
    Remove-Item -ErrorAction SilentlyContinue build/lifeking-native/WiiCompiled.exe
    # 60 FPS data patch (port/lifeking-mod60, made from the local game files; never in git).
    if (Test-Path (Join-Path $tools '..\lifeking-data\content\00000002.app')) {
        python -I (Join-Path $tools 'make_fps60_scripts.py') | Out-Null
        if ($LASTEXITCODE) { throw 'make_fps60_scripts failed' }
    }
    'build ok'
} finally { Pop-Location }
