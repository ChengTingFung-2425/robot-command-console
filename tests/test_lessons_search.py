"""
Tests for scripts/lessons_search.py

測試經驗教訓搜尋與管理工具的各項功能。
"""

import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path

# 確保 scripts/ 可被直接 import（須在第三方 import 前設定）
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest  # noqa: E402

from lessons_search import (  # noqa: E402
    filter_entries,
    find_stale_entries,
    format_entry,
    list_all_tags,
    parse_index,
    main,
    STANDARD_TAGS,
    VALID_PRIORITIES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_INDEX_CONTENT = textwrap.dedent("""\
    # Memory Index

    - title: Security Best Practices
      path: docs/memory/security_lessons.md
      tags: [security, token, auth, rbac, audit]
      priority: high
      author: copilot
      date: 2025-12-17
      review_date: 2026-06-17
      summary: Token 生成、動作驗證、密碼處理、審計日誌。

    - title: CLI Batch Operations
      path: docs/memory/cli_batch_lessons.md
      tags: [cli, batch, testing, performance, async]
      priority: medium
      author: copilot
      date: 2025-12-17
      review_date: 2026-06-17
      summary: TDD 流程、批次執行架構、錯誤處理。

    - title: Template
      path: docs/memory/TEMPLATE.md
      tags: [template]
      priority: low
      author: team
      date: 2025-12-17
      review_date: 2026-12-17
      summary: 記憶檔範本。
""")

SAMPLE_ENTRIES = [
    {
        "title": "Security Best Practices",
        "path": "docs/memory/security_lessons.md",
        "tags": ["security", "token", "auth", "rbac", "audit"],
        "priority": "high",
        "author": "copilot",
        "date": "2025-12-17",
        "review_date": "2026-06-17",
        "summary": "Token 生成、動作驗證、密碼處理、審計日誌。",
    },
    {
        "title": "CLI Batch Operations",
        "path": "docs/memory/cli_batch_lessons.md",
        "tags": ["cli", "batch", "testing", "performance", "async"],
        "priority": "medium",
        "author": "copilot",
        "date": "2025-12-17",
        "review_date": "2026-06-17",
        "summary": "TDD 流程、批次執行架構、錯誤處理。",
    },
    {
        "title": "Template",
        "path": "docs/memory/TEMPLATE.md",
        "tags": ["template"],
        "priority": "low",
        "author": "team",
        "date": "2025-12-17",
        "review_date": "2026-12-17",
        "summary": "記憶檔範本。",
    },
]


@pytest.fixture
def tmp_index(tmp_path) -> Path:
    """建立暫時的 INDEX.md 供測試使用。"""
    index_file = tmp_path / "INDEX.md"
    index_file.write_text(SAMPLE_INDEX_CONTENT, encoding="utf-8")
    return index_file


@pytest.fixture
def entries():
    """回傳範例條目清單。"""
    return [dict(e) for e in SAMPLE_ENTRIES]


# ---------------------------------------------------------------------------
# parse_index 測試
# ---------------------------------------------------------------------------

class TestParseIndex:
    """測試 INDEX.md 解析功能"""

    def test_parse_returns_entries(self, tmp_index):
        """確認解析結果包含正確數量的條目"""
        result = parse_index(tmp_index)
        assert len(result) == 3

    def test_parse_title(self, tmp_index):
        """確認 title 欄位正確解析"""
        result = parse_index(tmp_index)
        assert result[0]["title"] == "Security Best Practices"

    def test_parse_tags(self, tmp_index):
        """確認 tags 欄位解析為清單"""
        result = parse_index(tmp_index)
        assert "security" in result[0]["tags"]
        assert "token" in result[0]["tags"]

    def test_parse_priority(self, tmp_index):
        """確認 priority 欄位正確解析"""
        result = parse_index(tmp_index)
        assert result[0]["priority"] == "high"
        assert result[1]["priority"] == "medium"
        assert result[2]["priority"] == "low"

    def test_parse_review_date(self, tmp_index):
        """確認 review_date 欄位正確解析"""
        result = parse_index(tmp_index)
        assert result[0]["review_date"] == "2026-06-17"

    def test_parse_summary(self, tmp_index):
        """確認 summary 欄位正確解析"""
        result = parse_index(tmp_index)
        assert "Token" in result[0]["summary"]

    def test_parse_nonexistent_file(self, tmp_path):
        """不存在的檔案應回傳空清單"""
        result = parse_index(tmp_path / "nonexistent.md")
        assert result == []


# ---------------------------------------------------------------------------
# filter_entries 測試
# ---------------------------------------------------------------------------

class TestFilterEntries:
    """測試條目過濾功能"""

    def test_filter_by_tag(self, entries):
        """依標籤過濾"""
        result = filter_entries(entries, tag="security")
        assert len(result) == 1
        assert result[0]["title"] == "Security Best Practices"

    def test_filter_by_priority_high(self, entries):
        """依 high 優先級過濾"""
        result = filter_entries(entries, priority="high")
        assert len(result) == 1
        assert result[0]["priority"] == "high"

    def test_filter_by_priority_medium(self, entries):
        """依 medium 優先級過濾"""
        result = filter_entries(entries, priority="medium")
        assert len(result) == 1
        assert result[0]["priority"] == "medium"

    def test_filter_by_priority_low(self, entries):
        """依 low 優先級過濾"""
        result = filter_entries(entries, priority="low")
        assert len(result) == 1
        assert result[0]["priority"] == "low"

    def test_filter_by_keyword_in_title(self, entries):
        """依關鍵字過濾（標題）"""
        result = filter_entries(entries, keyword="CLI")
        assert len(result) == 1
        assert "CLI" in result[0]["title"]

    def test_filter_by_keyword_in_summary(self, entries):
        """依關鍵字過濾（摘要）"""
        result = filter_entries(entries, keyword="Token")
        assert len(result) == 1
        assert result[0]["title"] == "Security Best Practices"

    def test_filter_by_keyword_case_insensitive(self, entries):
        """關鍵字搜尋不分大小寫"""
        result = filter_entries(entries, keyword="token")
        assert len(result) == 1

    def test_filter_combined_tag_and_priority(self, entries):
        """同時使用 tag 和 priority 過濾"""
        result = filter_entries(entries, tag="security", priority="high")
        assert len(result) == 1

    def test_filter_combined_no_match(self, entries):
        """組合條件無符合結果"""
        result = filter_entries(entries, tag="security", priority="low")
        assert len(result) == 0

    def test_filter_no_criteria_returns_all(self, entries):
        """無過濾條件回傳全部"""
        result = filter_entries(entries)
        assert len(result) == 3

    def test_filter_nonexistent_tag(self, entries):
        """不存在的標籤回傳空清單"""
        result = filter_entries(entries, tag="nonexistent_tag_xyz")
        assert result == []


# ---------------------------------------------------------------------------
# find_stale_entries 測試
# ---------------------------------------------------------------------------

class TestFindStaleEntries:
    """測試過期條目偵測功能"""

    def test_finds_overdue_entry(self):
        """已超過 review_date stale_days 天的條目應被標記"""
        past_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        entries = [
            {"title": "Old Entry", "review_date": past_date},
            {"title": "Future Entry", "review_date": "2099-01-01"},
        ]
        stale = find_stale_entries(entries, stale_days=5)
        assert len(stale) == 1
        assert stale[0]["title"] == "Old Entry"

    def test_stale_days_threshold_respected(self):
        """當 stale_days 超過過期天數時，條目不應被標記"""
        past_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        entries = [{"title": "Old Entry", "review_date": past_date}]
        # 過期 10 天，但門檻設為 20 天 → 不應被標記
        stale = find_stale_entries(entries, stale_days=20)
        assert len(stale) == 0

    def test_stale_days_exact_boundary(self):
        """恰好達到 stale_days 門檻的條目應被標記"""
        past_date = (date.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        entries = [{"title": "Boundary Entry", "review_date": past_date}]
        stale = find_stale_entries(entries, stale_days=10)
        assert len(stale) == 1

    def test_no_review_date_is_stale(self):
        """沒有 review_date 的條目視為需複查"""
        entries = [{"title": "No Review", "summary": "test"}]
        stale = find_stale_entries(entries, stale_days=0)
        assert len(stale) == 1

    def test_future_review_date_not_stale(self):
        """review_date 未到的條目不應標記"""
        entries = [{"title": "Future", "review_date": "2099-12-31"}]
        stale = find_stale_entries(entries, stale_days=0)
        assert len(stale) == 0

    def test_empty_entries(self):
        """空清單回傳空清單"""
        assert find_stale_entries([], stale_days=90) == []


# ---------------------------------------------------------------------------
# format_entry 測試
# ---------------------------------------------------------------------------

class TestFormatEntry:
    """測試條目格式化輸出"""

    def test_format_contains_title(self, entries):
        """輸出應包含標題"""
        output = format_entry(entries[0])
        assert "Security Best Practices" in output

    def test_format_high_priority_icon(self, entries):
        """high 優先級應顯示紅色圖示"""
        output = format_entry(entries[0])
        assert "🔴" in output

    def test_format_medium_priority_icon(self, entries):
        """medium 優先級應顯示黃色圖示"""
        output = format_entry(entries[1])
        assert "🟡" in output

    def test_format_low_priority_icon(self, entries):
        """low 優先級應顯示白色圖示"""
        output = format_entry(entries[2])
        assert "⚪" in output

    def test_format_contains_path(self, entries):
        """輸出應包含路徑"""
        output = format_entry(entries[0])
        assert "docs/memory/security_lessons.md" in output

    def test_format_contains_tags(self, entries):
        """輸出應包含標籤"""
        output = format_entry(entries[0])
        assert "security" in output


# ---------------------------------------------------------------------------
# list_all_tags 測試（輸出驗證）
# ---------------------------------------------------------------------------

class TestListAllTags:
    """測試標籤統計功能"""

    def test_list_tags_output(self, entries, capsys):
        """輸出應包含使用的標籤"""
        list_all_tags(entries)
        captured = capsys.readouterr()
        assert "security" in captured.out
        assert "cli" in captured.out

    def test_nonstandard_tag_warning(self, capsys):
        """非標準標籤應顯示警告"""
        entries = [{"tags": ["unknown_nonstandard_tag_xyz"]}]
        list_all_tags(entries)
        captured = capsys.readouterr()
        assert "⚠️" in captured.out


# ---------------------------------------------------------------------------
# main() CLI 整合測試
# ---------------------------------------------------------------------------

class TestMainCLI:
    """測試 CLI 主程式整合"""

    def test_main_returns_zero_on_success(self, tmp_index):
        """成功搜尋應回傳 0"""
        rc = main(["--index", str(tmp_index), "--priority", "high"])
        assert rc == 0

    def test_main_list_tags(self, tmp_index, capsys):
        """--list-tags 應列出標籤"""
        rc = main(["--index", str(tmp_index), "--list-tags"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "security" in captured.out

    def test_main_filter_tag(self, tmp_index, capsys):
        """--tag 過濾應顯示對應條目"""
        rc = main(["--index", str(tmp_index), "--tag", "security"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Security Best Practices" in captured.out

    def test_main_filter_keyword(self, tmp_index, capsys):
        """--keyword 過濾應顯示對應條目"""
        rc = main(["--index", str(tmp_index), "--keyword", "Token"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Security Best Practices" in captured.out

    def test_main_stale_days(self, tmp_index, capsys):
        """--stale-days 應列出需複查的條目"""
        rc = main(["--index", str(tmp_index), "--stale-days", "99999"])
        assert rc == 0

    def test_main_returns_one_on_missing_index(self, tmp_path, capsys):
        """索引不存在應回傳 1"""
        rc = main(["--index", str(tmp_path / "missing.md")])
        assert rc == 1

    def test_main_no_args_shows_all(self, tmp_index, capsys):
        """無過濾條件時顯示全部條目"""
        rc = main(["--index", str(tmp_index)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Security Best Practices" in captured.out
        assert "CLI Batch Operations" in captured.out


# ---------------------------------------------------------------------------
# 標準標籤庫與優先級常數測試
# ---------------------------------------------------------------------------

class TestConstants:
    """測試標準常數定義"""

    def test_valid_priorities_set(self):
        """VALID_PRIORITIES 應包含三個等級"""
        assert VALID_PRIORITIES == {"high", "medium", "low"}

    def test_standard_tags_includes_key_tags(self):
        """STANDARD_TAGS 應包含核心標籤"""
        for tag in ["security", "testing", "tdd", "auth", "edge", "cloud"]:
            assert tag in STANDARD_TAGS

    def test_standard_tags_is_set(self):
        """STANDARD_TAGS 應為集合型態"""
        assert isinstance(STANDARD_TAGS, set)
