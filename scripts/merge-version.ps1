# 合并新版本 Android Studio 的英文资源，保留已有翻译
# 用法:
#   1. 将新版 AS 资源提取到 translations\en-new
#   2. .\scripts\merge-version.ps1 -FromDir translations\en-new -Backup

param(
    [Parameter(Mandatory = $true)]
    [string]$FromDir,

    [switch]$Backup
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$args = @("merge", "--from-dir", $FromDir)
if ($Backup) { $args += "--backup" }

python (Join-Path $Root "tools\translate_tool.py") @args
