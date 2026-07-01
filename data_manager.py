import csv
from datetime import datetime
from config import DATA_DIR


FIELDNAMES_TASK1 = [
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
    "retry_count"
]


def make_task1_filename(participant_id):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DATA_DIR / f"task1_{participant_id}_{now}.csv"


def save_task1_rows(filename, rows):
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES_TASK1)
        writer.writeheader()
        writer.writerows(rows)

