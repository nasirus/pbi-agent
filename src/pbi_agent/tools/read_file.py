from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from pbi_agent.tools.output import bound_output
from pbi_agent.tools.types import ToolContext, ToolSpec
from pbi_agent.tools.workspace_access import DEFAULT_MAX_LINES
from pbi_agent.tools.workspace_access import normalize_positive_int
from pbi_agent.tools.workspace_access import open_text_file
from pbi_agent.tools.workspace_access import relative_workspace_path
from pbi_agent.tools.workspace_access import resolve_safe_path

MAX_READ_FILE_OUTPUT_CHARS = 12_000
DATAFRAME_PREVIEW_ROWS = 5
DATAFRAME_SAMPLE_ROWS = 3

_TABULAR_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".parquet",
    ".json",
    ".feather",
    ".ipc",
    ".arrow",
}

SPEC = ToolSpec(
    name="read_file",
    description=(
        "Read a text file from the workspace with line-range support. "
        "Use this for safe cross-platform file inspection instead of shell commands."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "File path relative to the workspace root "
                    "(or absolute within workspace)."
                ),
            },
            "start_line": {
                "type": "integer",
                "description": "1-based starting line number. Defaults to 1.",
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum number of lines to return. Defaults to 200.",
            },
            "encoding": {
                "type": "string",
                "description": "Text encoding to use. Defaults to 'auto'.",
                "default": "auto",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
)


def handle(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    del context
    path_value = arguments.get("path", "")
    if not isinstance(path_value, str) or not path_value.strip():
        return {"error": "'path' must be a non-empty string."}

    root = Path.cwd().resolve()
    start_line = normalize_positive_int(arguments.get("start_line"), default=1)
    max_lines = normalize_positive_int(
        arguments.get("max_lines"), default=DEFAULT_MAX_LINES
    )
    encoding = arguments.get("encoding", "auto")

    try:
        target_path = resolve_safe_path(root, path_value)
        if not target_path.exists():
            return {"error": f"path not found: {target_path}"}
        if not target_path.is_file():
            return {"error": f"path is not a file: {target_path}"}

        suffix = target_path.suffix.lower()
        if suffix in _TABULAR_EXTENSIONS:
            return _handle_tabular_file(root, target_path, suffix)
        if suffix == ".pdf":
            return _handle_pdf_file(root, target_path)

        selected_lines: list[str] = []
        line_count = 0
        with open_text_file(target_path, encoding=str(encoding)) as text_handle:
            for line_count, line in enumerate(text_handle, start=1):
                if line_count < start_line:
                    continue
                if len(selected_lines) < max_lines:
                    selected_lines.append(line)

        selected = "".join(selected_lines)
        bounded_content, content_truncated = bound_output(
            selected, limit=MAX_READ_FILE_OUTPUT_CHARS
        )
        returned_start_line = start_line if selected_lines else 0
        returned_end_line = (
            returned_start_line + len(selected_lines) - 1 if selected_lines else 0
        )
        has_more_lines = returned_end_line < line_count if returned_end_line else False

        result: dict[str, Any] = {
            "path": relative_workspace_path(root, target_path),
            "start_line": returned_start_line,
            "end_line": returned_end_line,
            "total_lines": line_count,
            "content": bounded_content,
            "has_more_lines": has_more_lines,
        }
        if line_count == 0:
            result["empty"] = True
        if start_line > 1 or has_more_lines:
            result["windowed"] = True
        if content_truncated:
            result["content_truncated"] = True
        return result
    except Exception as exc:
        return {"error": bound_output(str(exc))[0]}


def _handle_tabular_file(root: Path, target_path: Path, suffix: str) -> dict[str, Any]:
    import polars as pl

    dataframe = _read_tabular_dataframe(target_path, suffix)
    schema = dataframe.schema
    rows = dataframe.height
    columns = dataframe.width
    column_names = list(schema.keys())
    column_types = {name: str(dtype) for name, dtype in schema.items()}

    datetime_columns = [
        name
        for name, dtype in schema.items()
        if dtype in {pl.Date, pl.Datetime, pl.Time}
    ]
    categorical_columns = [
        name
        for name, dtype in schema.items()
        if _is_categorical_column(dataframe, name, dtype)
    ]

    preview_rows = dataframe.head(DATAFRAME_PREVIEW_ROWS).to_dicts()
    sample_rows: list[dict[str, Any]] = []
    if rows > DATAFRAME_PREVIEW_ROWS:
        sample_size = min(DATAFRAME_SAMPLE_ROWS, rows)
        sample_rows = dataframe.sample(n=sample_size, shuffle=True, seed=42).to_dicts()

    numeric_summary = _numeric_summary(dataframe)
    null_counts = {
        column_name: int(null_count)
        for column_name, null_count in zip(
            dataframe.columns, dataframe.null_count().row(0), strict=True
        )
    }

    return {
        "path": relative_workspace_path(root, target_path),
        "file_type": suffix.lstrip("."),
        "rows": rows,
        "columns": columns,
        "column_names": column_names,
        "column_types": column_types,
        "datetime_columns": datetime_columns,
        "categorical_columns": categorical_columns,
        "preview": preview_rows,
        "sample": sample_rows,
        "metadata": {
            "null_counts": null_counts,
            "sample_strategy": (
                f"random({len(sample_rows)})"
                if sample_rows
                else f"head({len(preview_rows)})"
            ),
        },
        "numeric_summary": numeric_summary,
    }


def _read_tabular_dataframe(path: Path, suffix: str) -> Any:
    import polars as pl

    if suffix == ".csv":
        return pl.read_csv(path, try_parse_dates=True)
    if suffix == ".tsv":
        return pl.read_csv(path, separator="\t", try_parse_dates=True)
    if suffix in {".xlsx", ".xls"}:
        return pl.read_excel(path)
    if suffix == ".parquet":
        return pl.read_parquet(path)
    if suffix == ".json":
        return pl.read_json(path)
    if suffix in {".feather", ".ipc", ".arrow"}:
        return pl.read_ipc(path)
    raise ValueError(f"unsupported tabular file type: {suffix}")


def _is_categorical_column(dataframe: Any, name: str, dtype: Any) -> bool:
    import polars as pl

    if dtype in {pl.Categorical, pl.Enum}:
        return True
    if dtype != pl.String or dataframe.height == 0:
        return False

    non_null = dataframe[name].drop_nulls()
    if non_null.len() == 0:
        return False
    unique_ratio = non_null.n_unique() / non_null.len()
    return unique_ratio <= 0.2 and non_null.n_unique() <= 100


def _numeric_summary(dataframe: Any) -> dict[str, dict[str, float | int | None]]:
    summary: dict[str, dict[str, float | int | None]] = {}
    for column_name, dtype in dataframe.schema.items():
        if not dtype.is_numeric():
            continue
        series = dataframe[column_name].drop_nulls()
        if series.len() == 0:
            summary[column_name] = {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "std": None,
            }
            continue
        std_value = series.std()
        summary[column_name] = {
            "count": int(series.len()),
            "min": _safe_float(series.min()),
            "max": _safe_float(series.max()),
            "mean": _safe_float(series.mean()),
            "std": _safe_float(std_value),
        }
    return summary


def _safe_float(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    numeric = float(value)
    if math.isnan(numeric):
        return None
    return numeric


def _handle_pdf_file(root: Path, target_path: Path) -> dict[str, Any]:
    from pypdf import PdfReader

    reader = PdfReader(str(target_path))
    page_text = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(page_text)
    bounded_text, was_truncated = bound_output(
        full_text, limit=MAX_READ_FILE_OUTPUT_CHARS
    )

    metadata: dict[str, Any] = {"pages": len(reader.pages)}
    if reader.metadata:
        if reader.metadata.title:
            metadata["title"] = reader.metadata.title
        if reader.metadata.author:
            metadata["author"] = reader.metadata.author

    result: dict[str, Any] = {
        "path": relative_workspace_path(root, target_path),
        "file_type": "pdf",
        "content": bounded_text,
        "metadata": metadata,
    }
    if was_truncated:
        result["content_truncated"] = True
    return result
