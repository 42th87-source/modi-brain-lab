"""CSV persistence helpers for participant trial data."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from config import DATA_DIR


TASK1_FIELDNAMES = [
    "participant_id",
    "trial_index",
    "input_condition",
    "random_wait_ms",
    "stimulus_time",
    "response_start_time",
    "response_complete_time",
    "reaction_time_ms",
    "completion_time_ms",
    "gyro_pitch",
    "gyro_roll",
    "gyro_angular_velocity",
    "early_response",
    "delayed_response",
    "valid",
    "retry_count",
    "technical_error",
    "practice",
]

TASK2_FIELDNAMES = [
    "participant_id",
    "trial_index",
    "sensory_condition",
    "sequence_length",
    "target_sequence",
    "response_sequence",
    "position_correct_count",
    "exact_sequence_correct",
    "response_start_time",
    "response_complete_time",
    "total_response_time_ms",
    "random_seed",
    "practice",
]


def append_rows(csv_path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    """Append dictionaries to a CSV file, creating a header when needed."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def save_task1_trials(participant_id: str, rows: Iterable[dict]) -> Path:
    """Save TASK 1 raw trial rows for one participant."""

    csv_path = DATA_DIR / f"{participant_id}_task1_reaction.csv"
    append_rows(csv_path, rows, TASK1_FIELDNAMES)
    return csv_path


def save_task2_trials(participant_id: str, rows: Iterable[dict]) -> Path:
    """Save TASK 2 raw trial rows for one participant."""

    csv_path = DATA_DIR / f"{participant_id}_task2_memory.csv"
    append_rows(csv_path, rows, TASK2_FIELDNAMES)
    return csv_path
