# 无需 Gradle 的简易打包脚本（语言包专用）
# 用法: .\scripts\package.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Resources = Join-Path $Root "src\main\resources"
$DistDir = Join-Path $Root "build\distributions"
$PluginName = "Android-Studio-Chinese-1.0.0"
$Staging = Join-Path $Root "build\package-staging\$PluginName"

if (-not (Test-Path (Join-Path $Resources "META-INF\plugin.xml"))) {
    Write-Error "未找到 plugin.xml"
}

if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path (Join-Path $Staging "lib") | Out-Null
New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

$JarPath = Join-Path $Staging "lib\$PluginName.jar"
Push-Location $Resources
try {
    jar cf $JarPath .
    if ($LASTEXITCODE -ne 0) {
        # jar 命令不可用时用 Python 打包
        python -c "
import zipfile, os
from pathlib import Path
root = Path(r'$Resources')
jar = Path(r'$JarPath')
with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as zf:
    for p in root.rglob('*'):
        if p.is_file():
            zf.write(p, p.relative_to(root).as_posix())
print('packed', jar)
"
    }
}
finally {
    Pop-Location
}

$ZipPath = Join-Path $DistDir "$PluginName.zip"
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path $Staging -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Done: $ZipPath"
Write-Host "Install via: Settings > Plugins > Install Plugin from Disk"
