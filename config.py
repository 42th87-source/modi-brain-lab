"""Shared settings for the MODI cognitive measurement prototype."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


# TASK 1: reaction speed and input method
TASK1_TRIAL_SEQUENCE = [
    "button",
    "gyro",
    "gyro",
    "button",
    "gyro",
    "button",
    "button",
    "gyro",
]
TASK1_PRACTICE_SEQUENCE = ["button", "gyro"]

TASK1_RANDOM_WAIT_MS_MIN = 1500
TASK1_RANDOM_WAIT_MS_MAX = 3000
TASK1_MIN_VALID_REACTION_MS = 150
TASK1_DELAYED_REACTION_MS = 1500
TASK1_REQUIRED_VALID_PER_CONDITION = 3
TASK1_MAX_RETRY_PER_TRIAL = 3

GYRO_REACTION_ANGULAR_VELOCITY_DPS = 40.0
GYRO_COMPLETION_DELTA_DEGREES = 40.0
GYRO_RETURN_TOLERANCE_DEGREES = 10.0


# Pygame UI
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60

COLOR_BACKGROUND = (18, 22, 31)
COLOR_PANEL = (34, 41, 55)
COLOR_TEXT = (238, 242, 247)
COLOR_MUTED = (156, 163, 175)
COLOR_READY = (59, 130, 246)
COLOR_STIMULUS = (34, 197, 94)
COLOR_WARNING = (239, 68, 68)
COLOR_SUCCESS = (16, 185, 129)


# TASK 2: memory span and sensory integration
TASK2_TRIALS = [
    ("visual", 3),
    ("audiovisual", 3),
    ("audiovisual", 4),
    ("visual", 4),
    ("audiovisual", 5),
    ("visual", 5),
    ("visual", 6),
    ("audiovisual", 6),
]
TASK2_PRACTICE_TRIAL = ("visual", 2)
TASK2_STIMULUS_MS = 600
TASK2_BLANK_MS = 300

TASK2_COLORS = {
    "red": {
        "label": "빨강",
        "rgb": (239, 68, 68),
        "frequency": 262,
        "dial_range": "0~24",
        "key": "1",
    },
    "green": {
        "label": "초록",
        "rgb": (34, 197, 94),
        "frequency": 330,
        "dial_range": "25~49",
        "key": "2",
    },
    "blue": {
        "label": "파랑",
        "rgb": (59, 130, 246),
        "frequency": 392,
        "dial_range": "50~74",
        "key": "3",
    },
    "yellow": {
        "label": "노랑",
        "rgb": (250, 204, 21),
        "frequency": 523,
        "dial_range": "75~100",
        "key": "4",
    },
}
TASK2_COLOR_ORDER = ["red", "green", "blue", "yellow"]
