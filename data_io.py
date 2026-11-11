"""Flexible dataset import, explicit column mapping, and safe validation.

Accepted: CSV, TSV, TXT, Excel .xlsx, PTSP .dat.  Extra columns are ignored
only after start/finish mapping is clear. Ambiguous input requires user choice.
"""
from __future__ import annotations
import io
import math
import re
import pandas as pd
from alg import Task, validate_tasks

SYNONYMS = {
    "task_id": ("taskid", "id", "task", "taskname", "name", "job", "jobid", "activity", "activityid"),
    "start_time": ("starttime", "start", "begin", "begintime", "startingtime", "from", "startat"),
    "finish_time": ("finishtime", "finish", "end", "endtime", "stoptime", "stop", "endingtime", "to"),
}


def normalize_name(name: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def infer_columns(df: pd.DataFrame) -> dict[str, object | None]:
    """Return only high-confidence matches; never guess ambiguous columns."""
    result: dict[str, object | None] = {k: None for k in SYNONYMS}
    for target, choices in SYNONYMS.items():
        for choice in (normalize_name(target), *choices):
            matches = [col for col in df.columns if normalize_name(col) == choice]
            if len(matches) == 1:
                result[target] = matches[0]
                break
    if result["start_time"] is None or result["finish_time"] is None:
        if len(df.columns) == 2:
            # Unnamed headerless files are handled in read_input; 2 known columns
            # can be checked by caller, but not guessed from a named header.
            if all(str(c).startswith("column_") for c in df.columns):
                result["start_time"], result["finish_time"] = list(df.columns)
        elif len(df.columns) == 3 and all(str(c).startswith("column_") for c in df.columns):
            result.update(task_id=df.columns[0], start_time=df.columns[1], finish_time=df.columns[2])
    return result


def _is_number(text: object) -> bool:
    try:
        return math.isfinite(float(str(text).strip()))
    except (TypeError, ValueError):
        return False


def parse_ptsp(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    matches = [(i, int(m.group(1))) for i, line in enumerate(lines)
               if (m := re.match(r"^\s*Jobs\s*=\s*(\d+)\s*$", line, re.IGNORECASE))]
    if len(matches) != 1:
        raise ValueError("PTSP .dat: expected one 'Jobs = N' line.")
    startline, n = matches[0]
    if n <= 0:
        raise ValueError("PTSP .dat: Jobs count must be positive.")
    jobs = []
    for line in lines[startline+1:]:
        if len(jobs) >= n:
            break
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue
        vals = clean.split()
        if len(vals) != 2 or not all(_is_number(v) for v in vals):
            raise ValueError(f"PTSP .dat: expected two times for job {len(jobs)+1}.")
        jobs.append([f"T{len(jobs)+1:03d}", float(vals[0]), float(vals[1])])
    if len(jobs) != n:
        raise ValueError(f"PTSP .dat: declared {n} jobs but found {len(jobs)} pairs.")
    return pd.DataFrame(jobs, columns=["task_id", "start_time", "finish_time"])


def read_input(filename: str, content: bytes) -> tuple[pd.DataFrame, str]:
    """Parse bytes as a table; do not silently fix malformed data."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "xlsx":
        df = pd.read_excel(io.BytesIO(content), dtype=str, engine="openpyxl")
        return df, "Excel workbook, first worksheet"
    if suffix not in {"csv", "tsv", "txt", "dat"}:
        raise ValueError("File type not supported. Use CSV, TSV, TXT, XLSX or PTSP .dat.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("File must be UTF-8 text. Please export the file as UTF-8 CSV.") from exc
    if suffix == "dat" and re.search(r"^\s*Jobs\s*=", text, flags=re.M | re.I):
        return parse_ptsp(text), "Original PTSP .dat, Jobs section extracted"
    # Read ordinary delimited data; sep=None guesses comma/semicolon/tab/pipe.
    try:
        raw = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ValueError(f"Could not read this text table: {exc}") from exc
    raw.columns = [str(c).strip() for c in raw.columns]
    if raw.empty and text.strip():
        raise ValueError("No data rows were detected.")
    # Headerless numeric start/finish pairs: pandas treats first pair as headers.
    col_names = list(raw.columns)
    if len(col_names) in (2, 3) and all(_is_number(v) for v in col_names[-2:]):
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python", dtype=str, header=None, keep_default_na=False)
        df.columns = ["column_1", "column_2"] if len(df.columns) == 2 else ["column_1", "column_2", "column_3"]
        return df, "Headerless data (first row preserved)"
    # Known three-column with a header is already usable.
    return raw, "Detected delimited text table"


def make_tasks(df: pd.DataFrame, mapping: dict[str, object | None]) -> list[Task]:
    """Validate entire table. Display a precise row diagnostic on any failure."""
    start_col, finish_col = mapping.get("start_time"), mapping.get("finish_time")
    id_col = mapping.get("task_id")
    if start_col is None or finish_col is None or start_col not in df or finish_col not in df:
        raise ValueError("Select valid start-time and finish-time columns.")
    if start_col == finish_col:
        raise ValueError("Start and finish must be mapped to different columns.")
    if id_col is not None and (id_col not in df or id_col in (start_col, finish_col)):
        raise ValueError("Task ID must be blank or a distinct column.")
    if len(df) == 0:
        raise ValueError("At least one task is required.")
    tasks = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        task_id = str(row[id_col]).strip() if id_col is not None else f"T{i:03d}"
        if not task_id or task_id.lower() in {"nan", "none"}:
            raise ValueError(f"Data row {i}: empty task ID.")
        try:
            a, b = float(str(row[start_col]).strip()), float(str(row[finish_col]).strip())
        except (TypeError, ValueError):
            raise ValueError(f"Data row {i} ({task_id}): times must be numeric. Got {row[start_col]!r} and {row[finish_col]!r}.")
        tasks.append(Task(task_id, a, b))
    return validate_tasks(tasks)


def tasks_to_dataframe(tasks: list[Task]) -> pd.DataFrame:
    return pd.DataFrame([{"task_id": t.task_id, "start_time": t.start, "finish_time": t.finish} for t in tasks])
