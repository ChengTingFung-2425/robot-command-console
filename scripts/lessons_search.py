"""
Lessons Search & Management CLI Tool

用於搜尋、過濾及管理 docs/memory/INDEX.md 中的經驗教訓條目。

用法範例：
    python scripts/lessons_search.py --help
    python scripts/lessons_search.py --tag security
    python scripts/lessons_search.py --priority high
    python scripts/lessons_search.py --keyword token
    python scripts/lessons_search.py --stale-days 180
    python scripts/lessons_search.py --tag security --priority high --keyword token
"""

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path


# 標準標籤庫（供驗證與提示）
STANDARD_TAGS = {
    "security", "linting", "testing", "tdd", "architecture", "auth", "token",
    "edge", "cloud", "queue", "rabbitmq", "sqs", "ui", "cli", "batch",
    "database", "migration", "async", "performance", "datetime", "dataclass",
    "api", "flask", "fastapi", "tui", "llm", "launcher", "ops", "playbook",
    "device", "firmware", "rbac", "audit", "sync", "template",
    "cloud-sync", "javascript", "polling", "platform",
}

VALID_PRIORITIES = {"high", "medium", "low"}

PROJECT_ROOT = Path(__file__).parent.parent
INDEX_PATH = PROJECT_ROOT / "docs" / "memory" / "INDEX.md"


def parse_index(index_path: Path) -> list[dict]:
    """從 INDEX.md 解析所有條目（YAML-like 格式）。"""
    if not index_path.exists():
        return []

    text = index_path.read_text(encoding="utf-8")
    entries = []
    current: dict | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # 每個條目以 "- title:" 開頭
        title_match = re.match(r"^-\s+title:\s*(.+)", stripped)
        if title_match:
            if current is not None:
                entries.append(current)
            current = {"title": title_match.group(1).strip()}
            continue

        if current is None:
            continue

        # path
        path_match = re.match(r"path:\s*(.+)", stripped)
        if path_match:
            current["path"] = path_match.group(1).strip()
            continue

        # tags: [a, b, c]
        tags_match = re.match(r"tags:\s*\[(.+)\]", stripped)
        if tags_match:
            raw_tags = tags_match.group(1)
            current["tags"] = [t.strip() for t in raw_tags.split(",")]
            continue

        # priority
        priority_match = re.match(r"priority:\s*(.+)", stripped)
        if priority_match:
            current["priority"] = priority_match.group(1).strip()
            continue

        # author
        author_match = re.match(r"author:\s*(.+)", stripped)
        if author_match:
            current["author"] = author_match.group(1).strip()
            continue

        # date
        date_match = re.match(r"^date:\s*(.+)", stripped)
        if date_match:
            current["date"] = date_match.group(1).strip()
            continue

        # review_date
        review_match = re.match(r"review_date:\s*(.+)", stripped)
        if review_match:
            current["review_date"] = review_match.group(1).strip()
            continue

        # summary
        summary_match = re.match(r"summary:\s*(.+)", stripped)
        if summary_match:
            current["summary"] = summary_match.group(1).strip()
            continue

    if current is not None:
        entries.append(current)

    return entries


def filter_entries(
    entries: list[dict],
    tag: str | None = None,
    priority: str | None = None,
    keyword: str | None = None,
) -> list[dict]:
    """根據 tag、priority 和 keyword 過濾條目。"""
    result = []
    for entry in entries:
        if tag:
            entry_tags = entry.get("tags", [])
            if tag not in entry_tags:
                continue
        if priority:
            if entry.get("priority", "").lower() != priority.lower():
                continue
        if keyword:
            kw_lower = keyword.lower()
            haystack = " ".join([
                entry.get("title", ""),
                entry.get("summary", ""),
                " ".join(entry.get("tags", [])),
            ]).lower()
            if kw_lower not in haystack:
                continue
        result.append(entry)
    return result


def find_stale_entries(entries: list[dict], stale_days: int) -> list[dict]:
    """找出 review_date 已超過 stale_days 天的條目（需要複查）。"""
    today = date.today()
    stale = []
    for entry in entries:
        review_str = entry.get("review_date", "")
        if not review_str:
            stale.append(entry)
            continue
        try:
            review_date = datetime.strptime(review_str, "%Y-%m-%d").date()
            if (today - review_date).days >= stale_days:
                stale.append(entry)
        except ValueError:
            pass
    return stale


def format_entry(entry: dict) -> str:
    """格式化單個條目為可讀輸出。"""
    title = entry.get("title", "(no title)")
    path = entry.get("path", "")
    priority = entry.get("priority", "?")
    tags = ", ".join(entry.get("tags", []))
    date_str = entry.get("date", "")
    review_date = entry.get("review_date", "")
    summary = entry.get("summary", "")

    priority_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(priority, "❓")

    lines = [
        f"  {priority_icon} [{priority.upper()}] {title}",
        f"     📁 {path}",
        f"     🏷  {tags}",
        f"     📅 {date_str}" + (f"  （複查：{review_date}）" if review_date else ""),
        f"     📝 {summary}",
    ]
    return "\n".join(lines)


def print_results(entries: list[dict], header: str) -> None:
    """輸出搜尋結果。"""
    print(f"\n{header}")
    print("=" * 60)
    if not entries:
        print("  （無符合條目）")
    else:
        for entry in entries:
            print(format_entry(entry))
            print()
    print(f"共 {len(entries)} 筆")


def list_all_tags(entries: list[dict]) -> None:
    """列出索引中所有使用的標籤及出現次數。"""
    tag_count: dict[str, int] = {}
    for entry in entries:
        for tag in entry.get("tags", []):
            tag_count[tag] = tag_count.get(tag, 0) + 1
    print("\n📋 標籤統計")
    print("=" * 40)
    for tag, count in sorted(tag_count.items()):
        nonstandard = "" if tag in STANDARD_TAGS else "  ⚠️ (非標準)"
        print(f"  {tag}: {count} 筆{nonstandard}")


def build_parser() -> argparse.ArgumentParser:
    """建立命令列解析器。"""
    parser = argparse.ArgumentParser(
        description="經驗教訓搜尋與管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python scripts/lessons_search.py --tag security
  python scripts/lessons_search.py --priority high
  python scripts/lessons_search.py --keyword token
  python scripts/lessons_search.py --tag security --priority high
  python scripts/lessons_search.py --stale-days 180
  python scripts/lessons_search.py --list-tags
        """,
    )
    parser.add_argument("--tag", metavar="TAG", help="依標籤過濾（如 security、token）")
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="依優先級過濾",
    )
    parser.add_argument("--keyword", metavar="KW", help="依關鍵字搜尋（標題、摘要、標籤）")
    parser.add_argument(
        "--stale-days",
        type=int,
        metavar="DAYS",
        help="列出 review_date 已超過 N 天的條目（需複查）",
    )
    parser.add_argument("--list-tags", action="store_true", help="列出所有標籤及統計")
    parser.add_argument(
        "--index",
        default=str(INDEX_PATH),
        help=f"INDEX.md 路徑（預設：{INDEX_PATH}）",
    )
    return parser


def main(args: list[str] | None = None) -> int:
    """主程式入口，回傳結束碼。"""
    parser = build_parser()
    opts = parser.parse_args(args)

    index_path = Path(opts.index)
    entries = parse_index(index_path)

    if not entries:
        print(f"❌ 無法讀取或索引為空：{index_path}", file=sys.stderr)
        return 1

    if opts.list_tags:
        list_all_tags(entries)
        return 0

    if opts.stale_days is not None:
        stale = find_stale_entries(entries, opts.stale_days)
        print_results(stale, f"⏰ review_date 已過期的條目（今日：{date.today()}）")
        return 0

    # 一般搜尋
    filtered = filter_entries(
        entries,
        tag=opts.tag,
        priority=opts.priority,
        keyword=opts.keyword,
    )

    parts = []
    if opts.tag:
        parts.append(f"tag={opts.tag}")
    if opts.priority:
        parts.append(f"priority={opts.priority}")
    if opts.keyword:
        parts.append(f"keyword='{opts.keyword}'")
    header = "🔍 搜尋結果" + (f"（{', '.join(parts)}）" if parts else "（全部）")

    print_results(filtered, header)
    return 0


if __name__ == "__main__":
    sys.exit(main())
