$ErrorActionPreference = 'Stop'

$appName = 'Baixatudo'
$sourceApp = Join-Path $PSScriptRoot 'baixatudo.pyw'
$sourceLauncher = Join-Path $PSScriptRoot 'Iniciar Baixatudo.cmd'
$sourceYtDlp = Join-Path $PSScriptRoot 'yt-dlp.exe'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\Baixatudo'
$toolsDir = Join-Path $installDir 'tools'
$targetApp = Join-Path $installDir 'baixatudo.pyw'
$targetLauncher = Join-Path $installDir 'Iniciar Baixatudo.cmd'
$targetVbs = Join-Path $installDir 'Abrir Baixatudo.vbs'
$targetYtDlp = Join-Path $toolsDir 'yt-dlp.exe'
$startMenuDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$startMenuShortcut = Join-Path $startMenuDir 'Baixatudo.lnk'
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) 'Baixatudo.lnk'

function Test-PythonAvailable {
    $commands = @('pyw.exe', 'pythonw.exe', 'py.exe', 'python.exe')
    foreach ($command in $commands) {
        if (Get-Command $command -ErrorAction SilentlyContinue) {
            return $true
        }
    }

    $commonRoots = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        $env:ProgramFiles,
        ${env:ProgramFiles(x86)}
    )

    foreach ($root in $commonRoots) {
        if (-not $root -or -not (Test-Path -LiteralPath $root)) {
            continue
        }

        $found = Get-ChildItem -LiteralPath $root -Recurse -Filter 'pythonw.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            return $true
        }
    }

    return $false
}

foreach ($required in @($sourceApp, $sourceLauncher, $sourceYtDlp)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Arquivo necessario nao encontrado: $required"
    }
}

New-Item -ItemType Directory -Path $installDir -Force | Out-Null
New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null

Copy-Item -LiteralPath $sourceApp -Destination $targetApp -Force
Copy-Item -LiteralPath $sourceLauncher -Destination $targetLauncher -Force
Copy-Item -LiteralPath $sourceYtDlp -Destination $targetYtDlp -Force

@'
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
shell.Run """" & appDir & "\Iniciar Baixatudo.cmd" & """", 0, False
'@ | Set-Content -LiteralPath $targetVbs -Encoding ASCII

$shell = New-Object -ComObject WScript.Shell

$shortcut = $shell.CreateShortcut($startMenuShortcut)
$shortcut.TargetPath = "$env:WINDIR\System32\wscript.exe"
$shortcut.Arguments = "`"$targetVbs`""
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$env:WINDIR\System32\shell32.dll,220"
$shortcut.Save()

$shortcut = $shell.CreateShortcut($desktopShortcut)
$shortcut.TargetPath = "$env:WINDIR\System32\wscript.exe"
$shortcut.Arguments = "`"$targetVbs`""
$shortcut.WorkingDirectory = $installDir
$shortcut.IconLocation = "$env:WINDIR\System32\shell32.dll,220"
$shortcut.Save()

[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null

if (Test-PythonAvailable) {
    Start-Process -FilePath "$env:WINDIR\System32\wscript.exe" -ArgumentList "`"$targetVbs`"" -WorkingDirectory $installDir
    [System.Windows.Forms.MessageBox]::Show(
        "$appName foi instalado.`r`n`r`nAtalho criado na Area de Trabalho e no menu Iniciar.",
        $appName,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
}
else {
    [System.Windows.Forms.MessageBox]::Show(
        "$appName foi instalado, mas este computador precisa do Python para abrir o app.`r`n`r`nInstale o Python 3 para Windows e use o atalho Baixatudo.",
        $appName,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    ) | Out-Null
}
