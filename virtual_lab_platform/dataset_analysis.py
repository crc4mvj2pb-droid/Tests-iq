"""Local descriptive profiling for imported scientific CSV data.

This module performs data-quality diagnostics and descriptive statistics only.
It does not infer causality, repair data, or certify scientific validity.
"""
from __future__ import annotations
import csv, hashlib, math, statistics
from typing import Any

MAX_BYTES = 900_000
MAX_ROWS = 100_000
MAX_COLUMNS = 100
MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "missing", "."}

def analyze_csv(content: Any, *, preview_rows: int = 12) -> dict:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Provide CSV text to analyze.")
    raw = content.encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError(f"CSV exceeds the {MAX_BYTES}-byte analysis limit.")
    if isinstance(preview_rows, bool) or not isinstance(preview_rows, int) or not 1 <= preview_rows <= 50:
        raise ValueError("preview_rows must be an integer from 1 to 50.")
    try:
        reader = csv.reader(content.lstrip("\ufeff").splitlines())
        header = next(reader, None)
        if not header or not any(str(x).strip() for x in header):
            raise ValueError("CSV must contain a non-empty header row.")
        headers = [str(x).strip() for x in header]
        if len(headers) > MAX_COLUMNS:
            raise ValueError(f"CSV exceeds the {MAX_COLUMNS}-column limit.")
        if any(not x for x in headers):
            raise ValueError("Column names must not be empty.")
        if len(set(headers)) != len(headers):
            raise ValueError("Column names must be unique.")
        rows = []
        blank_lines = 0
        for line_no, row in enumerate(reader, start=2):
            if not row or not any(str(x).strip() for x in row):
                blank_lines += 1
                continue
            if len(row) != len(headers):
                raise ValueError(f"Row {line_no} has {len(row)} columns; expected {len(headers)}.")
            rows.append([str(x).strip() for x in row])
            if len(rows) > MAX_ROWS:
                raise ValueError(f"CSV exceeds the {MAX_ROWS}-row limit.")
    except UnicodeDecodeError:
        raise ValueError("CSV must be UTF-8 encoded.") from None
    if not rows:
        raise ValueError("CSV must contain at least one data row.")

    missing_by_column = {}
    numeric_by_column = {}
    columns = []
    for j, name in enumerate(headers):
        values = [row[j] for row in rows]
        missing = [v.casefold() in MISSING_TOKENS for v in values]
        present = [v for v, miss in zip(values, missing) if not miss]
        numeric = []
        all_numeric = bool(present)
        for v in present:
            try:
                n = float(v)
                if not math.isfinite(n):
                    all_numeric = False
                    break
                numeric.append(n)
            except (ValueError, TypeError):
                all_numeric = False
                break
        missing_count = sum(missing)
        missing_by_column[name] = missing_count
        summary = {
            "name": name,
            "non_missing": len(present),
            "missing": missing_count,
            "missing_fraction": missing_count / len(rows),
            "unique_non_missing": len(set(present)),
            "inferred_type": "numeric" if all_numeric else ("categorical/text" if present else "empty"),
        }
        if all_numeric:
            numeric_by_column[name] = numeric
            ordered = sorted(numeric)
            count = len(numeric)
            q = lambda p: ordered[(count - 1) * p // 1] if p in (0, 1) else _quantile(ordered, p)
            summary["statistics"] = {
                "count": count,
                "mean": statistics.fmean(numeric),
                "sample_sd": statistics.stdev(numeric) if count >= 2 else None,
                "min": ordered[0],
                "q1": q(0.25),
                "median": statistics.median(numeric),
                "q3": q(0.75),
                "max": ordered[-1],
                "sum": math.fsum(numeric),
            }
        else:
            counts = {}
            for v in present:
                counts[v] = counts.get(v, 0) + 1
            summary["top_values"] = [
                {"value": value, "count": count}
                for value, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
            ]
        columns.append(summary)

    duplicate_count = len(rows) - len({tuple(row) for row in rows})
    correlations = []
    numeric_names = list(numeric_by_column)
    for i, a in enumerate(numeric_names):
        for b in numeric_names[i + 1:]:
            pairs = []
            for row in rows:
                try:
                    x, y = float(row[headers.index(a)]), float(row[headers.index(b)])
                    if math.isfinite(x) and math.isfinite(y):
                        pairs.append((x, y))
                except (ValueError, TypeError):
                    continue
            if len(pairs) < 3:
                r, reason = None, "fewer_than_3_complete_pairs"
            else:
                xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
                sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
                if sx == 0 or sy == 0:
                    r, reason = None, "constant_column"
                else:
                    mx, my = statistics.fmean(xs), statistics.fmean(ys)
                    denom = math.sqrt(math.fsum((x-mx)**2 for x in xs) * math.fsum((y-my)**2 for y in ys))
                    r, reason = math.fsum((x-mx)*(y-my) for x,y in pairs)/denom, None
            correlations.append({"column_a": a, "column_b": b, "n": len(pairs), "pearson_r": r, "undefined_reason": reason})

    return {
        "analysis_type": "descriptive_csv_profile",
        "validation_status": "structural_and_descriptive_checks_only_not_scientific_validation",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "file_bytes": len(raw),
        "row_count": len(rows),
        "column_count": len(headers),
        "blank_lines_skipped": blank_lines,
        "duplicate_rows": duplicate_count,
        "duplicate_row_fraction": duplicate_count / len(rows),
        "columns": columns,
        "numeric_columns": numeric_names,
        "correlations": correlations,
        "preview": {"headers": headers, "rows": [dict(zip(headers, row)) for row in rows[:preview_rows]]},
        "warnings": [
            "Statistics are descriptive and do not establish causality or scientific validity.",
            "Numeric types are inferred from non-missing values; no domain-specific units or ranges are assumed.",
            "Pearson correlations are exploratory, sensitive to outliers, and do not imply causation.",
        ],
    }

def _quantile(sorted_values: list[float], p: float) -> float:
    pos = (len(sorted_values) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)
