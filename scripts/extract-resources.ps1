# 从 Android Studio 安装目录提取英文资源（调用 translate_tool.py）
# 用法: .\scripts\extract-resources.ps1 -StudioPath "C:\Program Files\Android\Android Studio"

param(
    [Parameter(Mandatory = $true)]
    [string]$StudioPath,

    [switch]$IncludePlugins,
    [switch]$Force
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$args = @("extract", "--studio-path", $StudioPath)
if ($IncludePlugins) { $args += "--include-plugins" }
if ($Force) { $args += "--force" }

python (Join-Path $Root "tools\translate_tool.py") @args
