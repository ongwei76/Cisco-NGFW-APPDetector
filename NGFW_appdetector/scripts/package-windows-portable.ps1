param(
    [string]$Version = "1.2.0"
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$distExe = Join-Path $root 'dist\ngfw-appdetector\ngfw-appdetector.exe'
if (-not (Test-Path $distExe)) {
    throw "Build output not found: $distExe. Run .\scripts\build-windows.ps1 -Clean first."
}

$releaseDir = Join-Path $root 'release'
$bundleName = "ngfw-appdetector-windows-portable-$Version"
$bundleDir = Join-Path $releaseDir $bundleName
$zipPath = Join-Path $releaseDir "$bundleName.zip"

if (-not (Test-Path $releaseDir)) {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}
if (Test-Path $bundleDir) {
    Remove-Item -Recurse -Force $bundleDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Path $bundleDir | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundleDir 'logs') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $bundleDir 'THIRD-PARTY-LICENSES') | Out-Null

Copy-Item -Recurse -Force (Join-Path $root 'dist\ngfw-appdetector') (Join-Path $bundleDir 'ngfw-appdetector')
Copy-Item -Force (Join-Path $root 'scripts\Start-NgfwAppDetector.bat') (Join-Path $bundleDir 'Start-NgfwAppDetector.bat')
Copy-Item -Force (Join-Path $root 'scripts\Stop-NgfwAppDetector.bat') (Join-Path $bundleDir 'Stop-NgfwAppDetector.bat')
Copy-Item -Force (Join-Path $root 'config.example.yaml') (Join-Path $bundleDir 'config.example.yaml')
Copy-Item -Force (Join-Path $root 'README.md') (Join-Path $bundleDir 'README.md')
Copy-Item -Force (Join-Path $root 'src\ngfw_appdetector\web\static\htmx.LICENSE') (Join-Path $bundleDir 'THIRD-PARTY-LICENSES\htmx.LICENSE')
Set-Content -Path (Join-Path $bundleDir 'VERSION.txt') -Value $Version -Encoding ASCII

$readme = @"
NGFW App Detector $Version - Windows Portable Bundle
NGFW App Detector $Version - Windows 便携分发包

中文快速开始：
1) 解压整个 ZIP；不要只运行压缩包内的 EXE。
2) 双击 Start-NgfwAppDetector.bat。
3) 浏览器将打开 http://127.0.0.1:8765。
4) 日志位于 logs\ngfw-appdetector-web.log。
5) 详细安装、组件、系统影响和使用说明请阅读 README.md。

停止：双击 Stop-NgfwAppDetector.bat。

English quick start:
1) Extract the entire ZIP; do not run the EXE from inside the archive.
2) Double-click Start-NgfwAppDetector.bat.
3) The browser opens http://127.0.0.1:8765.
4) Logs are written to logs\ngfw-appdetector-web.log.
5) Read README.md for complete installation, component, impact, and usage guidance.

Stop: double-click Stop-NgfwAppDetector.bat.
"@
Set-Content -Path (Join-Path $bundleDir 'README-Windows.txt') -Value $readme -Encoding UTF8

Compress-Archive -Path (Join-Path $bundleDir '*') -DestinationPath $zipPath -CompressionLevel Optimal

$hash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash
Set-Content -Path "$zipPath.sha256.txt" -Value "$hash  $([IO.Path]::GetFileName($zipPath))" -Encoding ASCII

Write-Host ""
Write-Host "Portable bundle created: $zipPath"
Write-Host "SHA256: $hash"
Write-Host "Distribute this zip; users can unzip and run Start-NgfwAppDetector.bat"
