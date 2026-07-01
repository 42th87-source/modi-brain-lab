"""시각 목표 반응과 청각 방해 억제를 측정하는 TASK 3을 실행한다."""

from __future__ import annotations

import random
import time
from typing import Any

import pygame

from modi_io import BaseModiIO, create_modi_io
from ui.widgets import COLORS, draw_text, draw_wrapped_text


TRIAL_ORDER = (
    "congruent", "visual_only", "audio_only", "congruent",
    "none", "audio_only", "visual_only", "congruent",
    "audio_only", "congruent", "visual_only", "audio_only",
    "congruent", "none", "visual_only", "congruent",
)
PRACTICE_ORDER = ("congruent", "audio_only")
RESPONSE_WINDOW_MS = 700
MIN_VALID_RT_MS = 150
STIMULUS_MS = 150


def _present_trial(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    condition: str,
    wait_ms: int,
    trial_index: int,
    total: int,
) -> dict[str, Any]:
    wait_started = time.perf_counter()
    early = False
    while (time.perf_counter() - wait_started) * 1000 < wait_ms:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        early = io.poll_button(events) or early
        surface.fill(COLORS["bg"])
        draw_text(surface, f"시행 {trial_index} / {total}", (45, 38), size=20, color=COLORS["muted"])
        draw_text(surface, "빛이 나오면 누르세요", surface.get_rect().center, size=34, bold=True, center=True)
        pygame.display.flip()
        clock.tick(60)

    has_light = condition in {"congruent", "visual_only"}
    has_sound = condition in {"congruent", "audio_only"}
    stimulus_started = time.perf_counter()
    if has_light:
        io.set_led(100, 100, 100)
    if has_sound:
        io.play_tone(523, 65)
    response_time: float | None = None
    while (time.perf_counter() - stimulus_started) * 1000 < RESPONSE_WINDOW_MS:
        elapsed_ms = (time.perf_counter() - stimulus_started) * 1000
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        if response_time is None and io.poll_button(events):
            response_time = elapsed_ms
        if elapsed_ms >= STIMULUS_MS:
            io.turn_off_led()
            io.stop_tone()
        surface.fill(COLORS["bg"])
        if has_light and elapsed_ms < STIMULUS_MS:
            pygame.draw.circle(surface, pygame.Color("white"), surface.get_rect().center, 85)
        draw_text(surface, "빛이 나오면 누르세요", (surface.get_width() // 2, 90), size=28, center=True)
        pygame.display.flip()
        clock.tick(60)
    io.turn_off_led()
    io.stop_tone()

    anticipatory = early or (response_time is not None and response_time < MIN_VALID_RT_MS)
    valid_press = response_time is not None and not anticipatory
    hit = has_light and valid_press
    miss = has_light and not valid_press
    false_alarm = not has_light and response_time is not None
    correct_rejection = not has_light and response_time is None
    return {
        "trial_index": trial_index,
        "stimulus_condition": condition,
        "random_wait_ms": wait_ms,
        "stimulus_time": round(stimulus_started, 6),
        "button_time": round(stimulus_started + response_time / 1000, 6) if response_time is not None else None,
        "reaction_time_ms": round(response_time, 1) if response_time is not None else None,
        "hit": hit,
        "miss": miss,
        "false_alarm": false_alarm,
        "correct_rejection": correct_rejection,
        "anticipatory_response": anticipatory,
    }


def run_task3(participant_id: str = "P001", io: BaseModiIO | None = None) -> dict[str, Any]:
    """TASK 3 전체 과정을 실행하고 공통 결과 딕셔너리를 반환한다."""

    owned_io = io is None
    io = io or create_modi_io()
    pygame.init()
    surface = pygame.display.set_mode((960, 640))
    pygame.display.set_caption("TASK 3 - 선택적 주의")
    clock = pygame.time.Clock()
    surface.fill(COLORS["bg"])
    draw_text(surface, "TASK 3. 선택적 주의", (480, 150), size=38, bold=True, center=True)
    draw_wrapped_text(
        surface,
        "빛이 나오면 버튼을 누르세요. 소리만 나오면 누르지 마세요.\n모의 모드에서는 스페이스 키를 사용합니다.",
        pygame.Rect(150, 230, 660, 130),
        size=24,
    )
    draw_text(surface, "Enter를 누르면 시작합니다.", (480, 440), size=22, color=COLORS["muted"], center=True)
    pygame.display.flip()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                waiting = False
        clock.tick(60)

    rng = random.Random(participant_id)
    try:
        for index, condition in enumerate(PRACTICE_ORDER, start=1):
            _present_trial(surface, clock, io, condition, 700, index, len(PRACTICE_ORDER))
        trials = [
            _present_trial(surface, clock, io, condition, rng.randint(800, 1500), index, len(TRIAL_ORDER))
            for index, condition in enumerate(TRIAL_ORDER, start=1)
        ]
        return {"task_id": "task3", "score": None, "metrics": {"device_mode": "mock" if io.is_mock else "real"}, "trials": trials}
    finally:
        io.turn_off_led()
        io.stop_tone()
        if owned_io:
            io.close()


run_task = run_task3
