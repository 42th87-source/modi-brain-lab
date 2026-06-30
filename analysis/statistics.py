"""참가자 요약 자료에서 개인·집단 통계와 조건 효과를 계산한다."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd


def load_participants_csv(path: str | Path) -> pd.DataFrame:
    """참가자 CSV를 읽고 점수 열을 숫자형으로 변환한다."""

    path = Path(path)
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, encoding="utf-8-sig")
    score_columns = [column for column in frame.columns if column.endswith("_score")]
    for column in [*score_columns, "total_score", "rank"]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def describe_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """점수별 참가자 수, 평균, 중앙값, 표준편차와 사분위수를 반환한다."""

    if frame.empty:
        return pd.DataFrame(columns=["count", "mean", "median", "std", "min", "q1", "q3", "max"])
    columns = [column for column in frame.columns if column.endswith("_score") or column == "total_score"]
    rows: dict[str, dict[str, float]] = {}
    for column in columns:
        series = pd.to_numeric(frame[column], errors="coerce").dropna()
        rows[column] = {
            "count": float(series.count()),
            "mean": float(series.mean()) if not series.empty else np.nan,
            "median": float(series.median()) if not series.empty else np.nan,
            "std": float(series.std(ddof=1)) if len(series) > 1 else 0.0,
            "min": float(series.min()) if not series.empty else np.nan,
            "q1": float(series.quantile(0.25)) if not series.empty else np.nan,
            "q3": float(series.quantile(0.75)) if not series.empty else np.nan,
            "max": float(series.max()) if not series.empty else np.nan,
        }
    return pd.DataFrame.from_dict(rows, orient="index").round(2)


def summarize_effects(reports: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    """개인 리포트에서 주요 인지과학 조건 효과의 집단 요약을 만든다."""

    metric_names = (
        "input_mode_difference_ms",
        "sensory_integration_effect",
        "auditory_interference_rate",
        "cursor_dual_task_cost",
        "rhythm_dual_task_cost_ms",
    )
    collected: dict[str, list[float]] = {name: [] for name in metric_names}
    for report in reports:
        metrics = report.get("metrics") or {}
        for name in metric_names:
            if metrics.get(name) is not None:
                collected[name].append(float(metrics[name]))

    return {
        name: {
            "count": len(values),
            "mean": round(float(np.mean(values)), 2) if values else None,
            "median": round(float(np.median(values)), 2) if values else None,
            "std": round(float(np.std(values, ddof=1)), 2) if len(values) > 1 else 0.0 if values else None,
        }
        for name, values in collected.items()
    }
