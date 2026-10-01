# 同步翻译到插件资源目录（调用 translate_tool.py）
# 用法: .\scripts\sync-translations.ps1 [-Clean]

param(
    [switch]$Clean
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$args = @("sync")
if ($Clean) { $args += "--clean" }

python (Join-Path $Root "tools\translate_tool.py") @args
