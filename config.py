"""프로젝트 전반에서 공유하는 경로와 측정 설정을 정의한다."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
TRIALS_DIR = DATA_DIR / "trials"
PARTICIPANTS_CSV = DATA_DIR / "participants.csv"

TASK_IDS = ("task1", "task2", "task3", "task4")
TASK_WEIGHTS = {task_id: 0.25 for task_id in TASK_IDS}
MIN_REFERENCE_COUNT = 10

PARTICIPANT_ID_MIN_LENGTH = 2
PARTICIPANT_ID_MAX_LENGTH = 16

# 예비실험 전 사용할 임시 반응시간 범위다. 값은 예비실험 후 교체한다.
REACTION_TIME_FALLBACK_MS = {
    "button": (150.0, 1_000.0),
    "gyro": (150.0, 1_000.0),
    "attention": (150.0, 700.0),
}

# TASK 1 자이로 기준값은 실제 장치 예비실험 후 보정한다.
GYRO_START_ANGULAR_VELOCITY = 40.0
GYRO_COMPLETE_ANGLE = 40.0

# pygame 공통 화면 설정
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 720
FPS = 60
COLOR_BG = "#0F1B2B"
COLOR_PANEL = "#16243B"
COLOR_PRIMARY = "#69A5FF"
COLOR_PRIMARY_HOVER = "#6FA3FF"
COLOR_SECONDARY = "#2A3B57"
COLOR_TEXT = "#F2F5FA"
COLOR_MUTED = "#BBC7DA"
COLOR_ERROR = "#FF6B6B"
COLOR_SUCCESS = "#4CD787"
COLOR_HIGHLIGHT = "#2E4060"
