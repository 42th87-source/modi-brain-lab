"""Score calculations for MODI cognitive tasks."""

from __future__ import annotations

from statistics import median
from typing import Iterable


def summarize_task1(rows: Iterable[dict]) -> dict:
    """Return representative TASK 1 reaction values from raw trial rows."""

    usable_rows = [
        row
        for row in rows
        if row.get("valid") is True
        and row.get("delayed_response") is False
        and row.get("practice") is False
    ]

    by_condition: dict[str, list[float]] = {"button": [], "gyro": []}
    for row in usable_rows:
        condition = row.get("input_condition")
        reaction_ms = row.get("reaction_time_ms")
        if condition in by_condition and isinstance(reaction_ms, (int, float)):
            by_condition[condition].append(float(reaction_ms))

    button_median = _median_or_none(by_condition["button"])
    gyro_median = _median_or_none(by_condition["gyro"])
    input_method_difference = None

    if button_median is not None and gyro_median is not None:
        input_method_difference = gyro_median - button_median

    return {
        "button_median_ms": button_median,
        "gyro_median_ms": gyro_median,
        "input_method_difference_ms": input_method_difference,
        "valid_button_trials": len(by_condition["button"]),
        "valid_gyro_trials": len(by_condition["gyro"]),
    }


def summarize_task2(rows: Iterable[dict]) -> dict:
    """Return TASK 2 condition scores and sensory integration effect."""

    usable_rows = [row for row in rows if row.get("practice") is False]
    condition_summaries = {
        condition: _summarize_task2_condition(usable_rows, condition)
        for condition in ("visual", "audiovisual")
    }

    visual_score = condition_summaries["visual"]["condition_score"]
    audiovisual_score = condition_summaries["audiovisual"]["condition_score"]
    task_score = None
    sensory_integration_effect = None

    if visual_score is not None and audiovisual_score is not None:
        task_score = round((visual_score + audiovisual_score) / 2, 1)

    visual_accuracy = condition_summaries["visual"]["position_accuracy"]
    audiovisual_accuracy = condition_summaries["audiovisual"]["position_accuracy"]
    if visual_accuracy is not None and audiovisual_accuracy is not None:
        sensory_integration_effect = round(audiovisual_accuracy - visual_accuracy, 1)

    return {
        "visual": condition_summaries["visual"],
        "audiovisual": condition_summaries["audiovisual"],
        "task2_score": task_score,
        "sensory_integration_effect": sensory_integration_effect,
    }


def _summarize_task2_condition(rows: list[dict], condition: str) -> dict:
    condition_rows = [
        row for row in rows if row.get("sensory_condition") == condition
    ]
    total_items = sum(int(row.get("sequence_length", 0)) for row in condition_rows)
    correct_items = sum(int(row.get("position_correct_count", 0)) for row in condition_rows)

    position_accuracy = None
    if total_items > 0:
        position_accuracy = round(correct_items / total_items * 100, 1)

    exact_lengths = [
        int(row.get("sequence_length", 0))
        for row in condition_rows
        if row.get("exact_sequence_correct") is True
    ]
    memory_span = max(exact_lengths) if exact_lengths else 0
    memory_span_score = round(memory_span / 6 * 100, 1)
    condition_score = None

    if position_accuracy is not None:
        condition_score = round(position_accuracy * 0.7 + memory_span_score * 0.3, 1)

    return {
        "position_accuracy": position_accuracy,
        "memory_span": memory_span,
        "memory_span_score": memory_span_score,
        "condition_score": condition_score,
    }


def _median_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return round(float(median(values)), 1)
