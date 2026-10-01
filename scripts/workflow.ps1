# Android Studio 汉化组一键工作流
# 用法:
#   .\scripts\workflow.ps1 extract -StudioPath "C:\Program Files\Android\Android Studio"
#   .\scripts\workflow.ps1 init
#   .\scripts\workflow.ps1 translate    # 应用术语表 + 导出待翻译
#   .\scripts\workflow.ps1 check
#   .\scripts\workflow.ps1 sync
#   .\scripts\workflow.ps1 build
#   .\scripts\workflow.ps1 all -StudioPath "..."

param(
    [Parameter(Position = 0)]
    [ValidateSet("extract", "init", "translate", "import", "check", "validate", "sync", "build", "merge", "all")]
    [string]$Step = "check",

    [string]$StudioPath,
    [switch]$IncludePlugins,
    [switch]$Force,
    [switch]$Backup,
    [string]$FromDir
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Tool = Join-Path $Root "tools\translate_tool.py"

function Invoke-Tool {
    param([string[]]$Args)
    python $Tool @Args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Push-Location $Root
try {
    switch ($Step) {
        "extract" {
            if (-not $StudioPath) {
                Write-Error "请指定 -StudioPath 参数"
            }
            $args = @("extract", "--studio-path", $StudioPath)
            if ($IncludePlugins) { $args += "--include-plugins" }
            if ($Force) { $args += "--force" }
            Invoke-Tool $args
        }
        "init" {
            $args = @("init")
            if ($Force) { $args += "--force" }
            Invoke-Tool $args
            Invoke-Tool @("glossary", "--apply")
        }
        "translate" {
            Invoke-Tool @("glossary", "--apply")
            Invoke-Tool @("export-todo")
            Write-Host ""
            Write-Host "待翻译任务已导出到 translations\work\todo.csv"
            Write-Host "翻译完成后运行: .\scripts\workflow.ps1 import"
        }
        "import" {
            Invoke-Tool @("import-todo", "--input", "translations/work/todo.csv")
        }
        "check" {
            Invoke-Tool @("check", "--format", "html")
        }
        "validate" {
            Invoke-Tool @("validate")
        }
        "merge" {
            $args = @("merge")
            if ($FromDir) { $args += @("--from-dir", $FromDir) }
            if ($Backup) { $args += "--backup" }
            Invoke-Tool $args
            Invoke-Tool @("glossary", "--apply")
        }
        "sync" {
            Invoke-Tool @("sync", "--clean")
        }
        "build" {
            Invoke-Tool @("sync", "--clean")
            if (Test-Path ".\gradlew.bat") {
                .\gradlew.bat buildPlugin
            } else {
                Write-Warning "未找到 gradlew.bat，请先在 Android Studio 中打开项目以生成 Wrapper"
            }
        }
        "all" {
            if (-not $StudioPath) {
                Write-Error "all 步骤需要 -StudioPath 参数"
            }
            & $MyInvocation.MyCommand.Path extract -StudioPath $StudioPath -IncludePlugins:$IncludePlugins -Force:$Force
            & $MyInvocation.MyCommand.Path init -Force
            & $MyInvocation.MyCommand.Path translate
            & $MyInvocation.MyCommand.Path check
            Write-Host ""
            Write-Host "初始化完成！请编辑 translations\work\todo.csv 完成翻译后运行:"
            Write-Host "  .\scripts\workflow.ps1 import"
            Write-Host "  .\scripts\workflow.ps1 sync"
            Write-Host "  .\scripts\workflow.ps1 build"
        }
    }
}
finally {
    Pop-Location
}
