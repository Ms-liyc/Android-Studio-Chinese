# 检查翻译进度（调用 translate_tool.py）
# 用法: .\scripts\check-untranslated.ps1 [-Html]

param(
    [switch]$Html,
    [switch]$Verbose
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$args = @("check")
if ($Html) { $args += @("--format", "html") }
if ($Verbose) { $args += "--verbose" }

python (Join-Path $Root "tools\translate_tool.py") @args
