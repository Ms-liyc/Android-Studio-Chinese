#!/usr/bin/env bash
# Android Studio 汉化组一键工作流（macOS / Linux）
# 用法: ./scripts/workflow.sh extract --studio-path "/Applications/Android Studio.app/Contents"

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOL="$ROOT/tools/translate_tool.py"
STEP="${1:-check}"

cd "$ROOT"

case "$STEP" in
  extract)
    python3 "$TOOL" extract --studio-path "$2" "${@:3}"
    ;;
  init)
    python3 "$TOOL" init --force
    python3 "$TOOL" glossary --apply
    ;;
  translate)
    python3 "$TOOL" glossary --apply
    python3 "$TOOL" export-todo
    echo "待翻译: translations/work/todo.csv"
    ;;
  import)
    python3 "$TOOL" import-todo --input translations/work/todo.csv
    ;;
  check)
    python3 "$TOOL" check --format html
    ;;
  validate)
    python3 "$TOOL" validate
    ;;
  sync)
    python3 "$TOOL" sync --clean
    ;;
  build)
    python3 "$TOOL" sync --clean
    ./gradlew buildPlugin
    ;;
  *)
    echo "用法: $0 {extract|init|translate|import|check|validate|sync|build}"
    exit 1
    ;;
esac
