from __future__ import annotations

from pathlib import Path

import pytest

from pbi_agent.tools import read_file as read_file_tool
from pbi_agent.tools.types import ToolContext


def test_read_file_returns_requested_line_window(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    result = read_file_tool.handle(
        {"path": "notes.txt", "start_line": 2, "max_lines": 2},
        ToolContext(),
    )

    assert result == {
        "path": "notes.txt",
        "start_line": 2,
        "end_line": 3,
        "total_lines": 4,
        "content": "two\nthree\n",
        "has_more_lines": True,
        "windowed": True,
    }


def test_read_file_auto_detects_utf16_bom(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "utf16.txt").write_bytes("hello\nworld\n".encode("utf-16"))

    result = read_file_tool.handle({"path": "utf16.txt"}, ToolContext())

    assert result["path"] == "utf16.txt"
    assert result["content"] == "hello\nworld\n"
    assert result["has_more_lines"] is False
    assert "windowed" not in result


def test_read_file_summarizes_csv_with_schema_and_stats(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("polars")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dataset.csv").write_text(
        "city,sales,ordered_at\nSeattle,10,2025-01-01\nSeattle,20,2025-01-02\nPortland,30,2025-01-03\n",
        encoding="utf-8",
    )

    result = read_file_tool.handle({"path": "dataset.csv"}, ToolContext())

    assert result["file_type"] == "csv"
    assert result["rows"] == 3
    assert result["columns"] == 3
    assert result["column_names"] == ["city", "sales", "ordered_at"]
    assert result["column_types"]["ordered_at"] == "Date"
    assert result["datetime_columns"] == ["ordered_at"]
    assert result["categorical_columns"] == ["city"]
    assert result["numeric_summary"]["sales"] == {
        "count": 3,
        "min": 10,
        "max": 30,
        "mean": 20.0,
        "std": 10.0,
    }


def test_read_file_summarizes_json_tabular_data(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("polars")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "dataset.json").write_text(
        '[{"name": "A", "value": 1}, {"name": "B", "value": 2}]',
        encoding="utf-8",
    )

    result = read_file_tool.handle({"path": "dataset.json"}, ToolContext())

    assert result["file_type"] == "json"
    assert result["rows"] == 2
    assert result["columns"] == 2
    assert result["column_types"]["value"] in {"Int64", "Int32"}


def test_read_file_summarizes_pdf_content_and_metadata(
    tmp_path: Path, monkeypatch
) -> None:
    pytest.importorskip("pypdf")
    monkeypatch.chdir(tmp_path)

    from pypdf import PdfWriter

    pdf_path = tmp_path / "report.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_metadata({"/Title": "Quarterly Report", "/Author": "Agent"})
    with pdf_path.open("wb") as file_handle:
        writer.write(file_handle)

    result = read_file_tool.handle({"path": "report.pdf"}, ToolContext())

    assert result["file_type"] == "pdf"
    assert result["metadata"]["pages"] == 1
    assert result["metadata"]["title"] == "Quarterly Report"
    assert result["metadata"]["author"] == "Agent"
    assert result["content"] == ""


def test_read_file_allows_more_than_default_output_budget(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    long_line = (
        f"prefix-{'x' * (read_file_tool.MAX_READ_FILE_OUTPUT_CHARS // 2)}-suffix"
    )
    (tmp_path / "large.txt").write_text(f"{long_line}\n", encoding="utf-8")

    result = read_file_tool.handle({"path": "large.txt"}, ToolContext())

    assert "content_truncated" not in result
    assert result["content"] == f"{long_line}\n"


def test_read_file_bounds_very_large_content(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    long_line = (
        f"prefix-{'x' * (read_file_tool.MAX_READ_FILE_OUTPUT_CHARS + 200)}-suffix"
    )
    (tmp_path / "large.txt").write_text(f"{long_line}\n", encoding="utf-8")

    result = read_file_tool.handle({"path": "large.txt"}, ToolContext())

    assert result["content_truncated"] is True
    assert len(result["content"]) <= read_file_tool.MAX_READ_FILE_OUTPUT_CHARS
    assert result["content"].startswith("prefix-")
    assert result["content"].endswith("-suffix\n")
    assert "chars omitted" in result["content"]


def test_read_file_rejects_binary_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02")

    result = read_file_tool.handle({"path": "blob.bin"}, ToolContext())

    assert "binary file is not supported" in result["error"]


def test_read_file_reports_empty_files_with_zero_range(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")

    result = read_file_tool.handle({"path": "empty.txt"}, ToolContext())

    assert result == {
        "path": "empty.txt",
        "start_line": 0,
        "end_line": 0,
        "total_lines": 0,
        "content": "",
        "has_more_lines": False,
        "empty": True,
    }
