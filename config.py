from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TRIAL_ORDER_TASK1 = [
    "button", "gyro", "gyro", "button",
    "gyro", "button", "button", "gyro"
]

RANDOM_WAIT_MIN_MS = 1500
RANDOM_WAIT_MAX_MS = 3000

PREDICTION_LIMIT_MS = 100
DELAY_LIMIT_MS = 1500

GYRO_ANGULAR_THRESHOLD = 40
GYRO_COMPLETE_ANGLE = 40
GYRO_RETURN_ANGLE = 10

POLL_INTERVAL = 0.005