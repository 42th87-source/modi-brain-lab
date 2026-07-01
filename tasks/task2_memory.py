"""색상 순서 기억과 감각 통합 효과를 측정하는 TASK 2를 실행한다."""

from __future__ import annotations

import hashlib
import random
import time
from typing import Any

import pygame

from modi_io import BaseModiIO, create_modi_io
from ui.widgets import COLORS as UI_COLORS, draw_text, draw_wrapped_text


COLOR_STIMULI = {
    "red": {
        "label": "빨강",
        "rgb": (100, 0, 0),
        "screen_rgb": pygame.Color(239, 68, 68),
        "frequency": 262,
        "dial_min": 0,
        "dial_max": 24,
    },
    "green": {
        "label": "초록",
        "rgb": (0, 100, 0),
        "screen_rgb": pygame.Color(34, 197, 94),
        "frequency": 330,
        "dial_min": 25,
        "dial_max": 49,
    },
    "blue": {
        "label": "파랑",
        "rgb": (0, 0, 100),
        "screen_rgb": pygame.Color(59, 130, 246),
        "frequency": 392,
        "dial_min": 50,
        "dial_max": 74,
    },
    "yellow": {
        "label": "노랑",
        "rgb": (100, 80, 0),
        "screen_rgb": pygame.Color(250, 204, 21),
        "frequency": 523,
        "dial_min": 75,
        "dial_max": 100,
    },
}
COLOR_ORDER = ("red", "green", "blue", "yellow")
TRIAL_ORDER = (
    ("visual", 3),
    ("audiovisual", 3),
    ("audiovisual", 4),
    ("visual", 4),
    ("audiovisual", 5),
    ("visual", 5),
    ("visual", 6),
    ("audiovisual", 6),
)
PRACTICE_TRIAL = ("visual", 2)
STIMULUS_MS = 600
BLANK_MS = 300
POST_SEQUENCE_PAUSE_MS = 350
CONFIRM_DEBOUNCE_MS = 180


def participant_seed(participant_id: str) -> int:
    """참가자 ID에서 재현 가능한 색상 순서용 난수 시드를 만든다."""

    digest = hashlib.sha256(str(participant_id).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def generate_sequence(rng: random.Random, length: int) -> list[str]:
    """같은 색상이 세 번 연속되지 않는 색상 순서를 생성한다."""

    sequence: list[str] = []
    while len(sequence) < length:
        color = rng.choice(COLOR_ORDER)
        if len(sequence) >= 2 and sequence[-1] == sequence[-2] == color:
            continue
        sequence.append(color)
    return sequence


def color_from_dial(value: float) -> str:
    """MODI 다이얼 값을 색상 이름으로 변환한다."""

    clamped = max(0.0, min(100.0, float(value)))
    for color_name in COLOR_ORDER:
        spec = COLOR_STIMULI[color_name]
        if spec["dial_min"] <= clamped <= spec["dial_max"]:
            return color_name
    return "yellow"


def _wait_for_start(surface: pygame.Surface, clock: pygame.time.Clock) -> None:
    while True:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        if any(
            event.type == pygame.KEYDOWN
            and event.key in (pygame.K_RETURN, pygame.K_SPACE)
            for event in events
        ):
            return
        surface.fill(UI_COLORS["bg"])
        draw_text(surface, "TASK 2. 기억력과 감각 통합", (surface.get_width() // 2, 165), size=36, bold=True, center=True)
        draw_wrapped_text(
            surface,
            "색상 순서를 기억한 뒤 다이얼로 색상을 고르고 버튼으로 확정하세요.\n"
            "시청각 조건에서는 색상과 함께 음높이가 제시됩니다.\n"
            "모의 모드에서는 좌우 방향키로 다이얼을 움직이고 Space 또는 Enter로 확정합니다.",
            pygame.Rect(150, 245, 690, 150),
            size=23,
            color=UI_COLORS["text"],
        )
        draw_text(surface, "Enter를 누르면 시작합니다.", (surface.get_width() // 2, 480), size=22, color=UI_COLORS["muted"], center=True)
        pygame.display.flip()
        clock.tick(60)


def _wait_for_confirm(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    title: str,
    detail: str,
) -> None:
    while True:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        if io.poll_button(events) or any(
            event.type == pygame.KEYDOWN
            and event.key in (pygame.K_RETURN, pygame.K_SPACE)
            for event in events
        ):
            return
        surface.fill(UI_COLORS["bg"])
        draw_text(surface, title, (surface.get_width() // 2, 230), size=34, bold=True, center=True)
        draw_wrapped_text(
            surface,
            detail,
            pygame.Rect(170, 300, 620, 90),
            size=22,
            color=UI_COLORS["muted"],
        )
        draw_text(surface, "버튼 또는 Enter를 누르면 시작합니다.", (surface.get_width() // 2, 460), size=21, center=True)
        pygame.display.flip()
        clock.tick(60)


def _present_sequence(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    sequence: list[str],
    condition: str,
) -> None:
    for index, color_name in enumerate(sequence, start=1):
        spec = COLOR_STIMULI[color_name]
        red, green, blue = spec["rgb"]
        io.set_led(red, green, blue)
        if condition == "audiovisual":
            io.play_tone(spec["frequency"], 60)
        started = time.perf_counter()
        while (time.perf_counter() - started) * 1000 < STIMULUS_MS:
            events = pygame.event.get()
            if any(event.type == pygame.QUIT for event in events):
                raise KeyboardInterrupt
            surface.fill(UI_COLORS["bg"])
            draw_text(surface, f"{index} / {len(sequence)}", (45, 38), size=20, color=UI_COLORS["muted"])
            pygame.draw.circle(surface, spec["screen_rgb"], surface.get_rect().center, 95)
            draw_text(surface, spec["label"], (surface.get_width() // 2, 475), size=34, bold=True, center=True)
            if condition == "audiovisual":
                draw_text(surface, f"{spec['frequency']}Hz", (surface.get_width() // 2, 525), size=21, color=UI_COLORS["muted"], center=True)
            pygame.display.flip()
            clock.tick(60)

        io.turn_off_led()
        io.stop_tone()
        blank_started = time.perf_counter()
        while (time.perf_counter() - blank_started) * 1000 < BLANK_MS:
            events = pygame.event.get()
            if any(event.type == pygame.QUIT for event in events):
                raise KeyboardInterrupt
            surface.fill(UI_COLORS["bg"])
            draw_text(surface, f"{index} / {len(sequence)}", (45, 38), size=20, color=UI_COLORS["muted"])
            draw_text(surface, "...", surface.get_rect().center, size=42, color=UI_COLORS["muted"], center=True)
            pygame.display.flip()
            clock.tick(60)

    io.turn_off_led()
    io.stop_tone()


def _draw_color_choices(
    surface: pygame.Surface,
    selected: str,
    response: list[str],
    expected_length: int,
) -> None:
    surface.fill(UI_COLORS["bg"])
    draw_text(surface, f"입력 {len(response) + 1} / {expected_length}", (surface.get_width() // 2, 72), size=30, bold=True, center=True)
    draw_text(surface, "다이얼로 색상을 고르고 버튼으로 확정하세요.", (surface.get_width() // 2, 116), size=20, color=UI_COLORS["muted"], center=True)

    box_size = 122
    gap = 30
    total_width = box_size * len(COLOR_ORDER) + gap * (len(COLOR_ORDER) - 1)
    start_x = (surface.get_width() - total_width) // 2
    y = 230
    for index, color_name in enumerate(COLOR_ORDER):
        spec = COLOR_STIMULI[color_name]
        rect = pygame.Rect(start_x + index * (box_size + gap), y, box_size, box_size)
        pygame.draw.rect(surface, spec["screen_rgb"], rect, border_radius=12)
        border = UI_COLORS["text"] if color_name == selected else UI_COLORS["highlight"]
        pygame.draw.rect(surface, border, rect, width=4, border_radius=12)
        draw_text(
            surface,
            spec["label"],
            (rect.centerx, rect.bottom + 28),
            size=18,
            center=True,
        )
        draw_text(
            surface,
            f"{spec['dial_min']}~{spec['dial_max']}",
            (rect.centerx, rect.bottom + 54),
            size=16,
            center=True,
            color=UI_COLORS["muted"],
        )

    labels = " ".join(COLOR_STIMULI[color]["label"] for color in response) or "-"
    draw_text(surface, f"입력됨: {labels}", (surface.get_width() // 2, 500), size=23, center=True)


def _collect_response(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    expected_length: int,
) -> tuple[list[str], float, float]:
    response: list[str] = []
    response_started = time.perf_counter()
    last_confirmed = -1.0
    selected = color_from_dial(io.get_dial_value())

    while len(response) < expected_length:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        if any(event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE for event in events):
            raise KeyboardInterrupt

        keyed_color = _color_from_number_key(events)
        if keyed_color is not None:
            selected = keyed_color

        selected = keyed_color or color_from_dial(io.get_dial_value())
        if io.poll_button(events):
            now = time.perf_counter()
            if (now - last_confirmed) * 1000 >= CONFIRM_DEBOUNCE_MS:
                response.append(selected)
                last_confirmed = now

        if len(response) < expected_length:
            _draw_color_choices(surface, selected, response, expected_length)
            pygame.display.flip()
        clock.tick(60)

    response_completed = time.perf_counter()
    return response, response_started, response_completed


def _color_from_number_key(events: list[pygame.event.Event]) -> str | None:
    key_map = {
        pygame.K_1: "red",
        pygame.K_2: "green",
        pygame.K_3: "blue",
        pygame.K_4: "yellow",
    }
    for event in events:
        if event.type == pygame.KEYDOWN and event.key in key_map:
            return key_map[event.key]
    return None


def _run_trial(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    *,
    trial_index: int,
    condition: str,
    sequence: list[str],
    random_seed: int,
    practice: bool,
) -> dict[str, Any]:
    label = "연습" if practice else f"시행 {trial_index} / {len(TRIAL_ORDER)}"
    condition_label = "시각" if condition == "visual" else "시청각"
    _wait_for_confirm(
        surface,
        clock,
        io,
        f"{label}: {condition_label} 조건",
        f"{len(sequence)}개의 색상 순서를 기억한 뒤 같은 순서로 입력합니다.",
    )

    _present_sequence(surface, clock, io, sequence, condition)
    pause_started = time.perf_counter()
    while (time.perf_counter() - pause_started) * 1000 < POST_SEQUENCE_PAUSE_MS:
        pygame.event.pump()
        clock.tick(60)

    response_sequence, response_started, response_completed = _collect_response(
        surface,
        clock,
        io,
        len(sequence),
    )
    correct_count = sum(
        1 for target, response in zip(sequence, response_sequence) if target == response
    )
    exact = sequence == response_sequence

    surface.fill(UI_COLORS["bg"])
    draw_text(
        surface,
        "정확합니다" if exact else f"{correct_count} / {len(sequence)}개 일치",
        (surface.get_width() // 2, 280),
        size=34,
        bold=True,
        center=True,
        color=UI_COLORS["success"] if exact else UI_COLORS["text"],
    )
    draw_text(surface, "다음 단계로 이동합니다.", (surface.get_width() // 2, 345), size=22, color=UI_COLORS["muted"], center=True)
    pygame.display.flip()
    pygame.time.wait(800)

    return {
        "trial_index": trial_index,
        "sensory_condition": condition,
        "sequence_length": len(sequence),
        "target_sequence": sequence,
        "response_sequence": response_sequence,
        "position_correct_count": correct_count,
        "exact_sequence_correct": exact,
        "response_start_time": round(response_started, 6),
        "response_complete_time": round(response_completed, 6),
        "total_response_time_ms": round((response_completed - response_started) * 1000, 1),
        "random_seed": random_seed,
        "practice": practice,
    }


def run_task2(participant_id: str = "P001", io: BaseModiIO | None = None) -> dict[str, Any]:
    """TASK 2 전체 과정을 실행하고 공통 결과 딕셔너리를 반환한다."""

    owned_io = io is None
    io = io or create_modi_io()
    pygame.init()
    surface = pygame.display.set_mode((960, 640))
    pygame.display.set_caption("TASK 2 - 기억력과 감각 통합")
    clock = pygame.time.Clock()
    random_seed = participant_seed(participant_id)
    rng = random.Random(random_seed)

    try:
        _wait_for_start(surface, clock)
        practice_condition, practice_length = PRACTICE_TRIAL
        _run_trial(
            surface,
            clock,
            io,
            trial_index=0,
            condition=practice_condition,
            sequence=generate_sequence(rng, practice_length),
            random_seed=random_seed,
            practice=True,
        )
        trials = [
            _run_trial(
                surface,
                clock,
                io,
                trial_index=index,
                condition=condition,
                sequence=generate_sequence(rng, sequence_length),
                random_seed=random_seed,
                practice=False,
            )
            for index, (condition, sequence_length) in enumerate(TRIAL_ORDER, start=1)
        ]
        return {
            "task_id": "task2",
            "score": None,
            "metrics": {"device_mode": "mock" if io.is_mock else "real"},
            "trials": trials,
        }
    finally:
        io.turn_off_led()
        io.stop_tone()
        if owned_io:
            io.close()


run_task = run_task2
