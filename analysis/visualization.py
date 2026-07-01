"""개인·집단 점수와 인지과학 조건 효과를 그래프로 표현한다."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Any

import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd


def _configure_korean_font() -> None:
    """사용 가능한 한글 글꼴을 matplotlib 기본 글꼴로 설정한다."""

    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ("Malgun Gothic", "NanumGothic", "AppleGothic"):
        if candidate in available:
            plt.rcParams["font.family"] = candidate
            plt.rcParams["axes.unicode_minus"] = False
            return


def create_score_overview(frame: pd.DataFrame):
    """TASK별 평균 점수와 종합점수 분포를 포함한 Figure를 만든다."""

    _configure_korean_font()
    figure, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    score_columns = [column for column in ("task1_score", "task2_score", "task3_score", "task4_score") if column in frame]
    if frame.empty or not score_columns:
        axes[0].text(0.5, 0.5, "아직 참가자 데이터가 없습니다.", ha="center", va="center")
        axes[1].axis("off")
        return figure

    means = frame[score_columns].apply(pd.to_numeric, errors="coerce").mean()
    axes[0].bar([name.replace("_score", "").upper() for name in means.index], means.values)
    axes[0].set_ylim(0, 100)
    axes[0].set_title("TASK별 평균 점수")
    axes[0].set_ylabel("점수")

    totals = pd.to_numeric(frame.get("total_score"), errors="coerce").dropna()
    if totals.empty:
        axes[1].text(0.5, 0.5, "종합점수가 없습니다.", ha="center", va="center")
    else:
        axes[1].hist(totals, bins=min(10, max(3, len(totals))), edgecolor="white")
        axes[1].axvline(totals.mean(), color="red", linestyle="--", label=f"평균 {totals.mean():.1f}")
        axes[1].legend()
    axes[1].set_title("종합점수 분포")
    axes[1].set_xlabel("점수")
    figure.tight_layout()
    return figure


def create_effect_overview(reports: Iterable[Mapping[str, Any]]):
    """참가자별 주요 조건 효과를 비교하는 Figure를 만든다."""

    _configure_korean_font()
    reports = list(reports)
    labels = [str(report.get("participant_id", index + 1)) for index, report in enumerate(reports)]
    metric_specs = (
        ("input_mode_difference_ms", "입력 방식 차이(ms)"),
        ("sensory_integration_effect", "감각 통합 정확도 차이"),
        ("auditory_interference_rate", "청각 간섭률(%)"),
        ("cursor_dual_task_cost", "커서 이중과제 비용"),
    )
    figure, axes = plt.subplots(2, 2, figsize=(11, 7))
    for axis, (metric, title) in zip(axes.flat, metric_specs):
        values = [(report.get("metrics") or {}).get(metric) for report in reports]
        pairs = [(label, value) for label, value in zip(labels, values) if value is not None]
        if not pairs:
            axis.text(0.5, 0.5, "자료 없음", ha="center", va="center")
            axis.set_title(title)
            continue
        axis.bar([pair[0] for pair in pairs], [float(pair[1]) for pair in pairs])
        axis.axhline(0, color="black", linewidth=0.8)
        axis.set_title(title)
        axis.tick_params(axis="x", rotation=45)
    figure.tight_layout()
    return figure


def save_figure(figure, path: str | Path) -> Path:
    """Figure를 PNG 파일로 저장하고 경로를 반환한다."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    return path
