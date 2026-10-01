#!/usr/bin/env python3
"""Android Studio 汉化组翻译工具链。"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_RE = re.compile(r"\{(\d+)\}")
PERCENT_RE = re.compile(r"%[sdif]")


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


@dataclass
class Config:
    en_dir: Path
    zh_dir: Path
    target_dir: Path
    glossary_path: Path
    glossary_keys_path: Path
    exclusions_path: Path
    state_path: Path
    work_dir: Path
    file_patterns: List[str]

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return cls(
            en_dir=ROOT / data["enDir"],
            zh_dir=ROOT / data["zhDir"],
            target_dir=ROOT / data["targetDir"],
            glossary_path=ROOT / data["glossaryPath"],
            glossary_keys_path=ROOT / data["glossaryKeysPath"],
            exclusions_path=ROOT / data["exclusionsPath"],
            state_path=ROOT / data["statePath"],
            work_dir=ROOT / data["workDir"],
            file_patterns=data.get("filePatterns", ["*.properties", "*.html", "*.xml"]),
        )


@dataclass
class Entry:
    key: str
    value: str
    comment: str = ""


@dataclass
class FileStats:
    rel_path: str
    total: int = 0
    translated: int = 0
    missing: int = 0
    untranslated: int = 0
    excluded: int = 0
    stale: int = 0
    invalid: int = 0
    missing_keys: List[str] = field(default_factory=list)
    untranslated_keys: List[str] = field(default_factory=list)
    stale_keys: List[str] = field(default_factory=list)
    invalid_keys: List[str] = field(default_factory=list)


def read_properties(path: Path) -> List[Entry]:
    if not path.exists():
        return []

    entries: List[Entry] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    pending_comment: List[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            pending_comment = []
            i += 1
            continue

        if stripped.startswith("#") or stripped.startswith("!"):
            pending_comment.append(line)
            i += 1
            continue

        key_part = line
        value_part = ""
        if "=" in line:
            key_part, value_part = line.split("=", 1)
        else:
            i += 1
            continue

        key = key_part.strip()
        value_lines = [value_part]

        while value_lines[-1].endswith("\\") and i + 1 < len(lines):
            i += 1
            value_lines[-1] = value_lines[-1][:-1]
            value_lines.append(lines[i])

        value = "\n".join(value_lines)
        entries.append(
            Entry(
                key=key,
                value=value,
                comment="\n".join(pending_comment),
            )
        )
        pending_comment = []
        i += 1

    return entries


def write_properties(path: Path, entries: Iterable[Entry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chunks: List[str] = []
    for entry in entries:
        if entry.comment:
            chunks.append(entry.comment)
        chunks.append(f"{entry.key}={entry.value}")
    path.write_text("\n".join(chunks) + ("\n" if chunks else ""), encoding="utf-8")


def entries_to_map(entries: Iterable[Entry]) -> Dict[str, str]:
    return {entry.key: entry.value for entry in entries}


def load_exclusions(path: Path) -> List[str]:
    if not path.exists():
        return []
    patterns: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def is_excluded(key: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns)


def iter_resource_files(base: Path, patterns: List[str]) -> List[Path]:
    files: Set[Path] = set()
    if not base.exists():
        return []
    for pattern in patterns:
        files.update(base.rglob(pattern))
    return sorted(files)


def relative_to(base: Path, path: Path) -> str:
    return path.relative_to(base).as_posix()


def extract_jar(jar_path: Path, output_dir: Path) -> int:
    count = 0
    with zipfile.ZipFile(jar_path) as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            target = output_dir / member
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(member))
            count += 1
    return count


def cmd_extract(args: argparse.Namespace, config: Config) -> int:
    studio_path = Path(args.studio_path)
    if not studio_path.exists():
        print(f"错误: Android Studio 路径不存在: {studio_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output) if args.output else config.en_dir
    if output_dir.exists() and not args.force:
        print(f"错误: 输出目录已存在: {output_dir}，使用 --force 覆盖", file=sys.stderr)
        return 1

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    jar_candidates: List[Path] = []
    lib_dir = studio_path / "lib"
    plugins_dir = studio_path / "plugins"

    if lib_dir.exists():
        jar_candidates.extend(lib_dir.rglob("resources_en*.jar"))
        jar_candidates.extend(
            p for p in lib_dir.rglob("*.jar") if "resources" in p.name.lower()
        )

    if args.include_plugins and plugins_dir.exists():
        for plugin_dir in plugins_dir.iterdir():
            plugin_lib = plugin_dir / "lib"
            if plugin_lib.exists():
                jar_candidates.extend(plugin_lib.rglob("resources_en*.jar"))

    jar_candidates = sorted(set(jar_candidates))
    if not jar_candidates:
        print("错误: 未找到任何 resources JAR 文件", file=sys.stderr)
        return 1

    merged_conflicts: List[str] = []
    extracted_files = 0

    for jar in jar_candidates:
        print(f"提取: {jar.name}")
        temp_dir = output_dir / "_tmp" / jar.stem
        temp_dir.mkdir(parents=True, exist_ok=True)
        extracted_files += extract_jar(jar, temp_dir)

        for src in temp_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(temp_dir)
            dest = output_dir / rel
            if dest.exists() and dest.read_bytes() != src.read_bytes():
                merged_conflicts.append(rel.as_posix())
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    shutil.rmtree(output_dir / "_tmp", ignore_errors=True)

    prop_count = len(list(output_dir.rglob("*.properties")))
    html_count = len(list(output_dir.rglob("*.html")))

    state = {
        "studioPath": str(studio_path),
        "extractedAt": datetime.now(timezone.utc).isoformat(),
        "jarCount": len(jar_candidates),
        "propertyFiles": prop_count,
        "htmlFiles": html_count,
        "conflicts": merged_conflicts,
    }
    config.state_path.parent.mkdir(parents=True, exist_ok=True)
    config.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print(f"提取完成: {len(jar_candidates)} 个 JAR, {prop_count} 个 .properties, {html_count} 个 .html")
    if merged_conflicts:
        print(f"警告: {len(merged_conflicts)} 个路径存在内容冲突（已使用最后提取的版本）")
    print(f"输出目录: {output_dir}")
    return 0


def cmd_init(args: argparse.Namespace, config: Config) -> int:
    if not config.en_dir.exists():
        print("错误: 请先运行 extract 提取英文资源", file=sys.stderr)
        return 1

    if config.zh_dir.exists() and not args.force:
        print(f"错误: 翻译目录已存在: {config.zh_dir}，使用 --force 覆盖", file=sys.stderr)
        return 1

    if config.zh_dir.exists():
        shutil.rmtree(config.zh_dir)

    shutil.copytree(config.en_dir, config.zh_dir)
    print(f"已初始化翻译目录: {config.zh_dir}")
    print("下一步: python tools/translate_tool.py glossary --apply")
    return 0


def load_glossary(path: Path) -> List[Tuple[str, str]]:
    if not path.exists():
        return []
    rows: List[Tuple[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = (row.get("source") or "").strip()
            target = (row.get("target") or "").strip()
            if source and target:
                rows.append((source, target))
    rows.sort(key=lambda item: len(item[0]), reverse=True)
    return rows


def load_key_glossary(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    mapping: Dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row.get("key") or "").strip()
            zh = (row.get("zh") or "").strip()
            if key and zh:
                mapping[key] = zh
    return mapping


def apply_phrase_glossary(text: str, glossary: List[Tuple[str, str]]) -> str:
    result = text
    for source, target in glossary:
        result = re.sub(rf"\b{re.escape(source)}\b", target, result)
    return result


def cmd_glossary(args: argparse.Namespace, config: Config) -> int:
    if not config.zh_dir.exists():
        print("错误: 请先运行 init 初始化翻译目录", file=sys.stderr)
        return 1

    phrase_glossary = load_glossary(config.glossary_path)
    key_glossary = load_key_glossary(config.glossary_keys_path)
    exclusions = load_exclusions(config.exclusions_path)

    updated_files = 0
    updated_entries = 0

    for en_file in iter_resource_files(config.en_dir, ["*.properties"]):
        rel = relative_to(config.en_dir, en_file)
        zh_file = config.zh_dir / rel
        if not zh_file.exists():
            continue

        en_entries = read_properties(en_file)
        zh_entries = read_properties(zh_file)
        zh_map = entries_to_map(zh_entries)
        changed = False

        new_entries: List[Entry] = []
        for entry in zh_entries:
            en_value = next((e.value for e in en_entries if e.key == entry.key), entry.value)
            if is_excluded(entry.key, exclusions):
                new_entries.append(entry)
                continue

            new_value = entry.value
            if entry.key in key_glossary:
                new_value = key_glossary[entry.key]
            elif entry.value == en_value and phrase_glossary:
                new_value = apply_phrase_glossary(entry.value, phrase_glossary)

            if new_value != entry.value:
                changed = True
                updated_entries += 1
                entry = Entry(key=entry.key, value=new_value, comment=entry.comment)

            new_entries.append(entry)

        for entry in en_entries:
            if entry.key in zh_map:
                continue
            value = key_glossary.get(entry.key, entry.value)
            if not is_excluded(entry.key, exclusions) and value == entry.value and phrase_glossary:
                value = apply_phrase_glossary(value, phrase_glossary)
            new_entries.append(Entry(key=entry.key, value=value, comment=entry.comment))
            changed = True
            updated_entries += 1

        if changed:
            write_properties(zh_file, new_entries)
            updated_files += 1

    if args.apply:
        print(f"术语表已应用: 更新 {updated_entries} 条 / {updated_files} 个文件")
    else:
        print(f"预览: 将影响约 {updated_entries} 条 / {updated_files} 个文件（加 --apply 执行）")
    return 0


def validate_placeholders(source: str, target: str) -> Optional[str]:
    src_nums = PLACEHOLDER_RE.findall(source)
    tgt_nums = PLACEHOLDER_RE.findall(target)
    if sorted(src_nums) != sorted(tgt_nums):
        return f"占位符不一致: {{{', '.join(src_nums)}}} -> {{{', '.join(tgt_nums)}}}"

    src_pct = PERCENT_RE.findall(source)
    tgt_pct = PERCENT_RE.findall(target)
    if sorted(src_pct) != sorted(tgt_pct):
        return f"格式符不一致: {src_pct} -> {tgt_pct}"

    if "&" in source and "&" not in target and "&&" not in source:
        return "可能缺少快捷键标记 &"
    return None


def analyze_file(
    en_file: Path,
    zh_file: Path,
    rel_path: str,
    exclusions: List[str],
    stale_map: Optional[Dict[str, str]] = None,
) -> FileStats:
    stats = FileStats(rel_path=rel_path)

    if en_file.suffix.lower() == ".properties":
        en_entries = read_properties(en_file)
        zh_map = entries_to_map(read_properties(zh_file)) if zh_file.exists() else {}

        for entry in en_entries:
            stats.total += 1
            if is_excluded(entry.key, exclusions):
                stats.excluded += 1
                continue

            zh_value = zh_map.get(entry.key)
            if zh_value is None:
                stats.missing += 1
                stats.missing_keys.append(entry.key)
            elif zh_value == entry.value:
                stats.untranslated += 1
                stats.untranslated_keys.append(entry.key)
            else:
                issue = validate_placeholders(entry.value, zh_value)
                if issue:
                    stats.invalid += 1
                    stats.invalid_keys.append(f"{entry.key}: {issue}")
                else:
                    stats.translated += 1

                if stale_map and entry.key in stale_map and stale_map[entry.key] != entry.value:
                    stats.stale += 1
                    stats.stale_keys.append(entry.key)
    else:
        if not zh_file.exists():
            stats.total = 1
            stats.missing = 1
            return stats

        en_text = en_file.read_text(encoding="utf-8")
        zh_text = zh_file.read_text(encoding="utf-8")
        stats.total = 1
        if zh_text == en_text:
            stats.untranslated = 1
        else:
            stats.translated = 1

    return stats


def cmd_check(args: argparse.Namespace, config: Config) -> int:
    if not config.en_dir.exists() or not config.zh_dir.exists():
        print("错误: 请先 extract 并 init", file=sys.stderr)
        return 1

    exclusions = load_exclusions(config.exclusions_path)
    all_stats: List[FileStats] = []

    for en_file in iter_resource_files(config.en_dir, config.file_patterns):
        rel = relative_to(config.en_dir, en_file)
        zh_file = config.zh_dir / rel
        stats = analyze_file(en_file, zh_file, rel, exclusions)
        all_stats.append(stats)

        if args.verbose and (
            stats.missing or stats.untranslated or stats.invalid or stats.stale
        ):
            print(f"[{rel}]")
            if stats.missing:
                print(f"  缺失: {stats.missing}")
            if stats.untranslated:
                print(f"  未翻译: {stats.untranslated}")
            if stats.stale:
                print(f"  原文变更: {stats.stale}")
            if stats.invalid:
                print(f"  校验失败: {stats.invalid}")

    total = sum(s.total for s in all_stats)
    translated = sum(s.translated for s in all_stats)
    missing = sum(s.missing for s in all_stats)
    untranslated = sum(s.untranslated for s in all_stats)
    excluded = sum(s.excluded for s in all_stats)
    invalid = sum(s.invalid for s in all_stats)
    stale = sum(s.stale for s in all_stats)
    effective = max(total - excluded, 1)
    progress = translated / effective * 100

    print()
    print("========== 翻译进度 ==========")
    print(f"总条目:     {total}")
    print(f"已排除:     {excluded}")
    print(f"已翻译:     {translated} ({progress:.1f}%)")
    print(f"未翻译:     {untranslated}")
    print(f"缺失 key:   {missing}")
    print(f"原文变更:   {stale}")
    print(f"校验失败:   {invalid}")

    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "excluded": excluded,
            "translated": translated,
            "untranslated": untranslated,
            "missing": missing,
            "stale": stale,
            "invalid": invalid,
            "progressPercent": round(progress, 2),
        },
        "files": [
            {
                "path": s.rel_path,
                "total": s.total,
                "translated": s.translated,
                "missing": s.missing,
                "untranslated": s.untranslated,
                "invalid": s.invalid,
                "stale": s.stale,
            }
            for s in all_stats
            if s.missing or s.untranslated or s.invalid or s.stale
        ],
    }

    config.work_dir.mkdir(parents=True, exist_ok=True)
    report_path = config.work_dir / "progress.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"详细报告: {report_path}")

    if args.format == "html":
        html = render_progress_html(report)
        html_path = config.work_dir / "progress.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"HTML 报告: {html_path}")

    return 1 if (missing or invalid) else 0


def render_progress_html(report: dict) -> str:
    summary = report["summary"]
    rows = "".join(
        f"<tr><td>{item['path']}</td><td>{item['translated']}/{item['total']}</td>"
        f"<td>{item['missing']}</td><td>{item['untranslated']}</td>"
        f"<td>{item['invalid']}</td><td>{item['stale']}</td></tr>"
        for item in report["files"]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>翻译进度报告</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; }}
    .summary {{ display: flex; gap: 16px; margin-bottom: 24px; }}
    .card {{ padding: 16px; border: 1px solid #ddd; border-radius: 8px; min-width: 120px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
  </style>
</head>
<body>
  <h1>Android Studio 汉化进度</h1>
  <p>生成时间: {report['generatedAt']}</p>
  <div class="summary">
    <div class="card"><strong>进度</strong><br>{summary['progressPercent']}%</div>
    <div class="card"><strong>已翻译</strong><br>{summary['translated']}</div>
    <div class="card"><strong>未翻译</strong><br>{summary['untranslated']}</div>
    <div class="card"><strong>缺失</strong><br>{summary['missing']}</div>
    <div class="card"><strong>校验失败</strong><br>{summary['invalid']}</div>
  </div>
  <table>
    <thead>
      <tr><th>文件</th><th>进度</th><th>缺失</th><th>未翻译</th><th>校验失败</th><th>原文变更</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>"""


def cmd_validate(args: argparse.Namespace, config: Config) -> int:
    args.verbose = True
    return cmd_check(args, config)


def cmd_merge(args: argparse.Namespace, config: Config) -> int:
    new_en_dir = Path(args.from_dir) if args.from_dir else config.en_dir
    backup_dir = config.work_dir / f"zh-CN-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    if not new_en_dir.exists():
        print(f"错误: 新英文目录不存在: {new_en_dir}", file=sys.stderr)
        return 1
    if not config.zh_dir.exists():
        print("错误: 翻译目录不存在，请先 init", file=sys.stderr)
        return 1

    if args.backup:
        shutil.copytree(config.zh_dir, backup_dir)
        print(f"已备份当前翻译到: {backup_dir}")

    added = removed = changed = carried = 0
    changelog: List[str] = []

    for en_file in iter_resource_files(new_en_dir, config.file_patterns):
        rel = relative_to(new_en_dir, en_file)
        zh_file = config.zh_dir / rel
        old_en_file = config.en_dir / rel

        if en_file.suffix.lower() == ".properties":
            new_entries = read_properties(en_file)
            old_entries = read_properties(old_en_file) if old_en_file.exists() else []
            zh_entries = read_properties(zh_file) if zh_file.exists() else []

            old_map = entries_to_map(old_entries)
            zh_map = entries_to_map(zh_entries)
            merged: List[Entry] = []

            for entry in new_entries:
                if entry.key not in old_map:
                    added += 1
                    changelog.append(f"ADD {rel} :: {entry.key}")
                    merged.append(Entry(key=entry.key, value=zh_map.get(entry.key, entry.value), comment=entry.comment))
                elif old_map[entry.key] != entry.value:
                    changed += 1
                    changelog.append(f"CHANGE {rel} :: {entry.key}")
                    if entry.key in zh_map and zh_map[entry.key] != old_map[entry.key]:
                        merged.append(Entry(key=entry.key, value=zh_map[entry.key], comment=entry.comment))
                        carried += 1
                    else:
                        merged.append(Entry(key=entry.key, value=entry.value, comment=entry.comment))
                else:
                    merged.append(
                        Entry(
                            key=entry.key,
                            value=zh_map.get(entry.key, entry.value),
                            comment=entry.comment,
                        )
                    )
                    if entry.key in zh_map and zh_map[entry.key] != entry.value:
                        carried += 1

            for key in old_map:
                if key not in entries_to_map(new_entries):
                    removed += 1
                    changelog.append(f"REMOVE {rel} :: {key}")

            write_properties(zh_file, merged)
        else:
            if not zh_file.exists() or zh_file.read_text(encoding="utf-8") == en_file.read_text(encoding="utf-8"):
                shutil.copy2(en_file, zh_file)

    if not args.no_replace_en:
        if config.en_dir.exists():
            shutil.rmtree(config.en_dir)
        shutil.copytree(new_en_dir, config.en_dir)

    changelog_path = config.work_dir / "merge-changelog.txt"
    config.work_dir.mkdir(parents=True, exist_ok=True)
    changelog_path.write_text("\n".join(changelog), encoding="utf-8")

    print("合并完成")
    print(f"  新增 key: {added}")
    print(f"  删除 key: {removed}")
    print(f"  原文变更: {changed}")
    print(f"  保留翻译: {carried}")
    print(f"变更日志: {changelog_path}")
    return 0


def cmd_export_todo(args: argparse.Namespace, config: Config) -> int:
    exclusions = load_exclusions(config.exclusions_path)
    config.work_dir.mkdir(parents=True, exist_ok=True)
    output = config.work_dir / (args.output or "todo.csv")

    rows: List[dict] = []
    for en_file in iter_resource_files(config.en_dir, ["*.properties"]):
        rel = relative_to(config.en_dir, en_file)
        zh_file = config.zh_dir / rel
        zh_map = entries_to_map(read_properties(zh_file)) if zh_file.exists() else {}

        for entry in read_properties(en_file):
            if is_excluded(entry.key, exclusions):
                continue
            zh_value = zh_map.get(entry.key)
            if zh_value is None or zh_value == entry.value:
                rows.append(
                    {
                        "file": rel,
                        "key": entry.key,
                        "en": entry.value,
                        "zh": zh_value or "",
                        "status": "missing" if zh_value is None else "untranslated",
                    }
                )

    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "key", "en", "zh", "status"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"已导出 {len(rows)} 条待翻译任务到 {output}")
    return 0


def cmd_import_todo(args: argparse.Namespace, config: Config) -> int:
    todo_path = Path(args.input)
    if not todo_path.exists():
        print(f"错误: 文件不存在: {todo_path}", file=sys.stderr)
        return 1

    updates: Dict[str, Dict[str, str]] = {}
    with todo_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            zh = (row.get("zh") or "").strip()
            if not zh:
                continue
            rel = row["file"]
            updates.setdefault(rel, {})[row["key"]] = zh

    changed_files = 0
    changed_entries = 0
    for rel, key_map in updates.items():
        zh_file = config.zh_dir / rel
        if not zh_file.exists():
            continue
        entries = read_properties(zh_file)
        file_changed = False
        new_entries: List[Entry] = []
        for entry in entries:
            if entry.key in key_map:
                entry = Entry(key=entry.key, value=key_map[entry.key], comment=entry.comment)
                file_changed = True
                changed_entries += 1
            new_entries.append(entry)
        if file_changed:
            write_properties(zh_file, new_entries)
            changed_files += 1

    print(f"已导入 {changed_entries} 条翻译到 {changed_files} 个文件")
    return 0


def cmd_sync(args: argparse.Namespace, config: Config) -> int:
    if not config.zh_dir.exists():
        print("错误: 翻译目录不存在", file=sys.stderr)
        return 1

    if args.clean and config.target_dir.exists():
        for pattern in config.file_patterns:
            for path in config.target_dir.rglob(pattern):
                if path.is_file():
                    path.unlink()

    count = 0
    for src in iter_resource_files(config.zh_dir, config.file_patterns):
        rel = relative_to(config.zh_dir, src)
        dest = config.target_dir / rel

        if src.suffix.lower() == ".properties":
            en_file = config.en_dir / rel
            if not en_file.exists():
                continue
            en_map = entries_to_map(read_properties(en_file))
            zh_entries = read_properties(src)
            translated_entries = [
                entry for entry in zh_entries
                if entry.key in en_map and entry.value != en_map[entry.key]
            ]
            if not translated_entries:
                continue
            write_properties(dest, translated_entries)
        else:
            en_file = config.en_dir / rel
            if en_file.exists() and src.read_text(encoding="utf-8") == en_file.read_text(encoding="utf-8"):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        count += 1

    print(f"已同步 {count} 个文件到 {config.target_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Android Studio 汉化组翻译工具")
    parser.add_argument(
        "--config",
        default=str(ROOT / "translations" / "config.json"),
        help="配置文件路径",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="从 Android Studio 提取英文资源")
    p_extract.add_argument("--studio-path", required=True, help="Android Studio 安装路径")
    p_extract.add_argument("--output", help="输出目录，默认 translations/en")
    p_extract.add_argument("--include-plugins", action="store_true", help="同时提取 bundled 插件资源")
    p_extract.add_argument("--force", action="store_true", help="覆盖已有输出目录")

    p_init = sub.add_parser("init", help="从英文目录初始化 zh-CN 工作区")
    p_init.add_argument("--force", action="store_true")

    p_glossary = sub.add_parser("glossary", help="应用术语表")
    p_glossary.add_argument("--apply", action="store_true", help="写入文件（默认仅预览）")

    p_check = sub.add_parser("check", help="检查翻译进度")
    p_check.add_argument("--verbose", action="store_true")
    p_check.add_argument("--format", choices=["text", "html"], default="text")

    sub.add_parser("validate", help="校验翻译（占位符等）")

    p_merge = sub.add_parser("merge", help="合并新版本英文资源")
    p_merge.add_argument("--from-dir", help="新版本的英文目录")
    p_merge.add_argument("--backup", action="store_true", help="合并前备份 zh-CN")
    p_merge.add_argument("--no-replace-en", action="store_true", help="不替换 translations/en")

    p_export = sub.add_parser("export-todo", help="导出待翻译 CSV")
    p_export.add_argument("--output", default="todo.csv")

    p_import = sub.add_parser("import-todo", help="从 CSV 导入翻译")
    p_import.add_argument("--input", default="translations/work/todo.csv")

    p_sync = sub.add_parser("sync", help="同步已翻译内容到插件资源目录")
    p_sync.add_argument("--clean", action="store_true", help="同步前清理目标目录中的旧资源")

    return parser


def main() -> int:
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()
    config = Config.load(Path(args.config))

    commands = {
        "extract": cmd_extract,
        "init": cmd_init,
        "glossary": cmd_glossary,
        "check": cmd_check,
        "validate": cmd_validate,
        "merge": cmd_merge,
        "export-todo": cmd_export_todo,
        "import-todo": cmd_import_todo,
        "sync": cmd_sync,
    }
    return commands[args.command](args, config)


if __name__ == "__main__":
    raise SystemExit(main())
