$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $root 'dist'
$buildDir = Join-Path $root '.build'
$payloadRoot = Join-Path $buildDir ("installer_payload_" + [Guid]::NewGuid().ToString('N'))
$payloadZip = Join-Path $buildDir 'BaixatudoPayload.zip'
$setupExe = Join-Path $distDir 'Baixatudo-Setup.exe'
$sourceApp = Join-Path $root 'baixatudo.pyw'
$sourceLauncher = Join-Path $root 'Iniciar Baixatudo.cmd'
$sourceYtDlp = Join-Path $root 'tools\yt-dlp.exe'
$installerSource = Join-Path $PSScriptRoot 'StandaloneInstaller.cs'
$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'

foreach ($required in @($sourceApp, $sourceLauncher, $sourceYtDlp, $installerSource, $csc)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Arquivo necessario nao encontrado: $required"
    }
}

New-Item -ItemType Directory -Path $distDir -Force | Out-Null
New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $payloadRoot 'tools') -Force | Out-Null

Copy-Item -LiteralPath $sourceApp -Destination (Join-Path $payloadRoot 'baixatudo.pyw') -Force
Copy-Item -LiteralPath $sourceLauncher -Destination (Join-Path $payloadRoot 'Iniciar Baixatudo.cmd') -Force
Copy-Item -LiteralPath $sourceYtDlp -Destination (Join-Path $payloadRoot 'tools\yt-dlp.exe') -Force

if (Test-Path -LiteralPath $payloadZip) {
    Remove-Item -LiteralPath $payloadZip -Force
}

Compress-Archive -Path (Join-Path $payloadRoot '*') -DestinationPath $payloadZip -CompressionLevel Optimal -Force

& $csc `
    /nologo `
    /target:winexe `
    /platform:anycpu `
    /out:$setupExe `
    /resource:$payloadZip,BaixatudoPayload.zip `
    /reference:System.Windows.Forms.dll `
    /reference:System.IO.Compression.dll `
    /reference:System.IO.Compression.FileSystem.dll `
    $installerSource

if ($LASTEXITCODE -ne 0) {
    throw "Falha ao compilar o instalador."
}

if (-not (Test-Path -LiteralPath $setupExe)) {
    throw "O instalador nao foi criado: $setupExe"
}

Write-Host "Instalador criado: $setupExe"
