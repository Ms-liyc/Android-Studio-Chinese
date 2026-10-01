# 从 CSV 导入翻译结果
# 用法: .\scripts\import-todo.ps1 [-Input translations\work\todo.csv]

param(
    [string]$Input = "translations\work\todo.csv"
)

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
python (Join-Path $Root "tools\translate_tool.py") import-todo --input $Input
