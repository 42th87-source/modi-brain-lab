"""테스트별 점수, 종합점수와 백분위 점수를 계산한다."""

from __future__ import annotations

from statistics import median
from typing import Any, Iterable, Mapping

from config import MIN_REFERENCE_COUNT, REACTION_TIME_FALLBACK_MS, TASK_IDS


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """값을 지정된 범위로 제한한다."""

    return max(minimum, min(maximum, float(value)))


def _numbers(values: Iterable[Any]) -> list[float]:
    return [float(value) for value in values if value is not None]


def median_or_none(values: Iterable[Any]) -> float | None:
    """숫자 목록의 중앙값을 반환하고 값이 없으면 None을 반환한다."""

    numbers = _numbers(values)
    return float(median(numbers)) if numbers else None


def percentile_score(
    value: float | None,
    references: Iterable[Any] = (),
    *,
    lower_is_better: bool = False,
    fallback_bounds: tuple[float, float] | None = None,
) -> float | None:
    """집단 내 백분위를 0~100점으로 변환한다.

    기준 자료가 부족하면 지정된 임시 범위를 선형 변환한다.
    """

    if value is None:
        return None
    value = float(value)
    samples = _numbers(references)
    if len(samples) >= MIN_REFERENCE_COUNT:
        less = sum(sample < value for sample in samples)
        equal = sum(sample == value for sample in samples)
        percentile = 100.0 * (less + 0.5 * equal) / len(samples)
        return round(100.0 - percentile if lower_is_better else percentile, 2)

    if fallback_bounds is None:
        return None
    low, high = map(float, fallback_bounds)
    if high <= low:
        raise ValueError("fallback_bounds의 최댓값은 최솟값보다 커야 합니다.")
    ratio = (value - low) / (high - low)
    score = 100.0 * (1.0 - ratio if lower_is_better else ratio)
    return round(clamp(score), 2)


def score_task1(
    result: Mapping[str, Any],
    *,
    button_references: Iterable[Any] = (),
    gyro_references: Iterable[Any] = (),
) -> dict[str, Any]:
    """TASK 1의 버튼·자이로 중앙값과 입력 방식 차이를 계산한다."""

    metrics = dict(result.get("metrics") or {})
    trials = list(result.get("trials") or [])

    def trial_times(condition: str) -> list[float]:
        return [
            float(trial["reaction_time_ms"])
            for trial in trials
            if trial.get("input_condition") == condition
            and trial.get("reaction_time_ms") is not None
            and trial.get("valid", True)
            and not trial.get("early_response", False)
            and not trial.get("delayed_response", False)
        ]

    button_median = metrics.get("button_median_ms")
    gyro_median = metrics.get("gyro_median_ms")
    button_median = float(button_median) if button_median is not None else median_or_none(trial_times("button"))
    gyro_median = float(gyro_median) if gyro_median is not None else median_or_none(trial_times("gyro"))

    button_score = percentile_score(
        button_median,
        button_references,
        lower_is_better=True,
        fallback_bounds=REACTION_TIME_FALLBACK_MS["button"],
    )
    gyro_score = percentile_score(
        gyro_median,
        gyro_references,
        lower_is_better=True,
        fallback_bounds=REACTION_TIME_FALLBACK_MS["gyro"],
    )
    component_scores = [score for score in (button_score, gyro_score) if score is not None]
    score = round(sum(component_scores) / len(component_scores), 2) if component_scores else None
    return {
        "score": score,
        "metrics": {
            **metrics,
            "button_median_ms": button_median,
            "gyro_median_ms": gyro_median,
            "input_mode_difference_ms": (
                round(gyro_median - button_median, 2)
                if button_median is not None and gyro_median is not None
                else None
            ),
            "button_percentile_score": button_score,
            "gyro_percentile_score": gyro_score,
        },
    }


def score_task2(result: Mapping[str, Any]) -> dict[str, Any]:
    """TASK 2의 조건별 위치 정확도, 기억 폭과 감각 통합 효과를 계산한다."""

    metrics = dict(result.get("metrics") or {})
    trials = list(result.get("trials") or [])
    condition_metrics: dict[str, dict[str, float]] = {}
    for condition in ("visual", "audiovisual"):
        selected = [trial for trial in trials if trial.get("sensory_condition") == condition]
        total_items = sum(int(trial.get("sequence_length", 0)) for trial in selected)
        correct_items = sum(int(trial.get("position_correct_count", 0)) for trial in selected)
        metric_prefix = "visual" if condition == "visual" else "audiovisual"
        accuracy = 100.0 * correct_items / total_items if total_items else metrics.get(f"{metric_prefix}_accuracy")
        accuracy = float(accuracy) if accuracy is not None else None
        exact_lengths = [
            int(trial.get("sequence_length", 0))
            for trial in selected
            if trial.get("exact_sequence_correct", False)
        ]
        span = max(exact_lengths, default=0)
        if not selected and metrics.get(f"{metric_prefix}_memory_span") is not None:
            span = int(metrics[f"{metric_prefix}_memory_span"])
        span_score = 100.0 * span / 6.0
        condition_score = 0.7 * accuracy + 0.3 * span_score if accuracy is not None else None
        condition_metrics[condition] = {
            "position_accuracy": round(accuracy, 2) if accuracy is not None else None,
            "memory_span": float(span),
            "score": round(condition_score, 2) if condition_score is not None else None,
        }

    scores = [value["score"] for value in condition_metrics.values() if value["score"] is not None]
    score = round(sum(scores) / len(scores), 2) if scores else None
    visual_accuracy = condition_metrics["visual"]["position_accuracy"]
    audiovisual_accuracy = condition_metrics["audiovisual"]["position_accuracy"]
    integration_effect = (
        round(audiovisual_accuracy - visual_accuracy, 2)
        if visual_accuracy is not None and audiovisual_accuracy is not None
        else None
    )
    return {
        "score": score,
        "metrics": {
            **metrics,
            "visual_accuracy": visual_accuracy,
            "audiovisual_accuracy": audiovisual_accuracy,
            "visual_memory_span": condition_metrics["visual"]["memory_span"],
            "audiovisual_memory_span": condition_metrics["audiovisual"]["memory_span"],
            "sensory_integration_effect": integration_effect,
        },
    }


def score_task3(
    result: Mapping[str, Any], *, reaction_references: Iterable[Any] = ()
) -> dict[str, Any]:
    """TASK 3의 적중률, 억제 성공률, 청각 간섭률과 점수를 계산한다."""

    metrics = dict(result.get("metrics") or {})
    trials = list(result.get("trials") or [])
    light_trials = [trial for trial in trials if trial.get("stimulus_condition") in {"congruent", "visual_only"}]
    no_light_trials = [trial for trial in trials if trial.get("stimulus_condition") in {"audio_only", "none"}]
    audio_trials = [trial for trial in trials if trial.get("stimulus_condition") == "audio_only"]

    hit_rate = 100.0 * sum(bool(trial.get("hit")) for trial in light_trials) / len(light_trials) if light_trials else 0.0
    inhibition = 100.0 * sum(bool(trial.get("correct_rejection")) for trial in no_light_trials) / len(no_light_trials) if no_light_trials else 0.0
    interference = 100.0 * sum(bool(trial.get("false_alarm")) for trial in audio_trials) / len(audio_trials) if audio_trials else 0.0
    balanced_accuracy = (hit_rate + inhibition) / 2.0
    reaction_median = median_or_none(
        trial.get("reaction_time_ms") for trial in light_trials if trial.get("hit")
    )
    reaction_score = percentile_score(
        reaction_median,
        reaction_references,
        lower_is_better=True,
        fallback_bounds=REACTION_TIME_FALLBACK_MS["attention"],
    )
    score = 0.8 * balanced_accuracy + 0.2 * (reaction_score or 0.0)
    if balanced_accuracy < 50.0:
        score = 0.8 * balanced_accuracy
        reaction_score = 0.0
    return {
        "score": round(clamp(score), 2),
        "metrics": {
            **metrics,
            "hit_rate": round(hit_rate, 2),
            "inhibition_success_rate": round(inhibition, 2),
            "balanced_accuracy": round(balanced_accuracy, 2),
            "auditory_interference_rate": round(interference, 2),
            "reaction_median_ms": reaction_median,
            "reaction_percentile_score": reaction_score,
        },
    }


def score_task4(result: Mapping[str, Any]) -> dict[str, Any]:
    """TASK 4의 커서 유지율, 비트 오차와 이중과제 비용을 계산한다."""

    metrics = dict(result.get("metrics") or {})
    trials = list(result.get("trials") or [])

    def phase_rows(phase: str) -> list[Mapping[str, Any]]:
        return [trial for trial in trials if trial.get("phase") == phase]

    dual = phase_rows("dual_task")
    cursor_baseline = phase_rows("cursor_baseline")
    rhythm_baseline = phase_rows("rhythm_baseline")

    def cursor_rate(rows: list[Mapping[str, Any]]) -> float | None:
        cursor_rows = [row for row in rows if row.get("inside_target") is not None]
        return 100.0 * sum(bool(row.get("inside_target")) for row in cursor_rows) / len(cursor_rows) if cursor_rows else None

    def beat_error(rows: list[Mapping[str, Any]]) -> float | None:
        values = [abs(float(row["beat_error_ms"])) for row in rows if row.get("beat_error_ms") is not None]
        return sum(values) / len(values) if values else None

    dual_cursor = cursor_rate(dual)
    baseline_cursor = cursor_rate(cursor_baseline)
    dual_error = beat_error(dual)
    baseline_error = beat_error(rhythm_baseline)
    rhythm_accuracy = clamp(100.0 - dual_error / 4.0) if dual_error is not None else 0.0
    misses = sum(bool(row.get("missed_beat")) for row in dual)
    extras = sum(bool(row.get("extra_press")) for row in dual)
    rhythm_score = clamp(rhythm_accuracy - min(30.0, 5.0 * (misses + extras)))
    score = None if dual_cursor is None else round(0.5 * dual_cursor + 0.5 * rhythm_score, 2)
    return {
        "score": score,
        "metrics": {
            **metrics,
            "dual_cursor_hold_rate": round(dual_cursor, 2) if dual_cursor is not None else None,
            "dual_mean_beat_error_ms": dual_error,
            "rhythm_score": round(rhythm_score, 2),
            "cursor_dual_task_cost": (
                round(baseline_cursor - dual_cursor, 2)
                if baseline_cursor is not None and dual_cursor is not None
                else None
            ),
            "rhythm_dual_task_cost_ms": (
                round(dual_error - baseline_error, 2)
                if dual_error is not None and baseline_error is not None
                else None
            ),
            "missed_beats": misses,
            "extra_presses": extras,
        },
    }


def score_task(
    result: Mapping[str, Any], *, references: Mapping[str, Iterable[Any]] | None = None
) -> dict[str, Any]:
    """task_id에 맞는 점수 계산기를 호출해 표준 결과를 반환한다."""

    references = references or {}
    task_id = str(result.get("task_id"))
    if task_id == "task1":
        calculated = score_task1(
            result,
            button_references=references.get("button", ()),
            gyro_references=references.get("gyro", ()),
        )
    elif task_id == "task2":
        calculated = score_task2(result)
    elif task_id == "task3":
        calculated = score_task3(result, reaction_references=references.get("attention", ()))
    elif task_id == "task4":
        calculated = score_task4(result)
    else:
        raise ValueError(f"알 수 없는 task_id입니다: {task_id}")

    return {
        **dict(result),
        "task_id": task_id,
        "score": calculated["score"],
        "metrics": calculated["metrics"],
        "trials": list(result.get("trials") or []),
    }


def calculate_total_score(
    task_scores: Mapping[str, float | None], *, require_all: bool = False
) -> float | None:
    """완료된 테스트 점수의 동일 가중 평균을 계산한다."""

    if require_all and any(task_scores.get(task_id) is None for task_id in TASK_IDS):
        return None
    values = [float(task_scores[task_id]) for task_id in TASK_IDS if task_scores.get(task_id) is not None]
    return round(sum(values) / len(values), 1) if values else None
