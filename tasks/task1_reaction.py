"""버튼과 자이로 입력의 반응시간 차이를 측정하는 TASK 1을 실행한다."""

from __future__ import annotations

import math
import random
import time
from statistics import median
from typing import Any

import pygame

from config import GYRO_COMPLETE_ANGLE, GYRO_START_ANGULAR_VELOCITY
from modi_io import BaseModiIO, GyroState, create_modi_io
from ui.widgets import COLORS, draw_text, draw_wrapped_text


TRIAL_ORDER = ("button", "gyro", "gyro", "button", "gyro", "button", "button", "gyro")
PRACTICE_ORDER = ("button", "gyro")
WAIT_RANGE_MS = (1500, 3000)
MIN_VALID_RT_MS = 100
MAX_VALID_RT_MS = 1500
RESPONSE_TIMEOUT_MS = 3000
RETURN_ANGLE = 10.0


def angular_speed(state: GyroState) -> float:
    """세 축 각속도의 크기를 반환한다."""

    return math.sqrt(
        state.angular_velocity_x**2
        + state.angular_velocity_y**2
        + state.angular_velocity_z**2
    )


def angle_displacement(state: GyroState, neutral: GyroState) -> float:
    """시작 자세에서 pitch 또는 roll이 이동한 최대 각도를 반환한다."""

    return max(abs(state.pitch - neutral.pitch), abs(state.roll - neutral.roll))


def _wait_for_continue(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    title: str,
    detail: str,
) -> None:
    while True:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        if any(
            event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE)
            for event in events
        ):
            return
        surface.fill(COLORS["bg"])
        draw_text(surface, title, (surface.get_width() // 2, 205), size=35, bold=True, center=True)
        draw_wrapped_text(
            surface,
            detail,
            pygame.Rect(165, 280, 630, 125),
            size=22,
            color=COLORS["muted"],
        )
        draw_text(
            surface,
            "Enter를 누르면 시작합니다.",
            (surface.get_width() // 2, 470),
            size=21,
            center=True,
        )
        pygame.display.flip()
        clock.tick(60)


def _draw_waiting(surface: pygame.Surface, condition: str, label: str) -> None:
    surface.fill(COLORS["bg"])
    draw_text(surface, label, (40, 35), size=20, color=COLORS["muted"])
    instruction = "버튼을 누르세요" if condition == "button" else "손잡이를 한 번 돌리세요"
    draw_text(surface, "신호를 기다리세요", surface.get_rect().center, size=36, bold=True, center=True)
    draw_text(
        surface,
        f"신호가 나오면 {instruction}",
        (surface.get_width() // 2, 420),
        size=22,
        color=COLORS["muted"],
        center=True,
    )


def _input_started(io: BaseModiIO, condition: str, events: list[pygame.event.Event]) -> bool:
    if condition == "button":
        return io.poll_button(events)
    return angular_speed(io.get_gyro()) >= GYRO_START_ANGULAR_VELOCITY


def _wait_for_gyro_return(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    neutral: GyroState,
) -> None:
    """다음 시행 전에 손잡이가 기준 자세로 돌아오기를 기다린다."""

    started = time.perf_counter()
    while angle_displacement(io.get_gyro(), neutral) > RETURN_ANGLE:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        surface.fill(COLORS["bg"])
        draw_text(surface, "손잡이를 가운데로 돌려놓으세요", surface.get_rect().center, size=30, center=True)
        pygame.display.flip()
        clock.tick(60)
        if time.perf_counter() - started > 8:
            break


def _run_trial(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    *,
    condition: str,
    trial_index: int,
    total: int,
    practice: bool,
    rng: random.Random,
) -> dict[str, Any]:
    label = f"연습 {trial_index} / {total}" if practice else f"시행 {trial_index} / {total}"
    neutral = io.get_gyro()
    wait_ms = rng.randint(*WAIT_RANGE_MS)
    wait_started = time.perf_counter()
    early = False

    while (time.perf_counter() - wait_started) * 1000 < wait_ms:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        early = _input_started(io, condition, events) or early
        _draw_waiting(surface, condition, label)
        pygame.display.flip()
        clock.tick(60)
        if early:
            break

    if early:
        io.turn_off_led()
        io.stop_tone()
        return {
            "trial_index": trial_index,
            "input_condition": condition,
            "random_wait_ms": wait_ms,
            "reaction_time_ms": None,
            "completion_time_ms": None,
            "early_response": True,
            "delayed_response": False,
            "valid": False,
            "practice": practice,
        }

    io.set_led(100, 100, 100)
    io.play_tone(880, 65)
    stimulus_time = time.perf_counter()
    response_started: float | None = None
    response_completed: float | None = None
    response_state = GyroState()

    while (time.perf_counter() - stimulus_time) * 1000 < RESPONSE_TIMEOUT_MS:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        state = io.get_gyro()
        if condition == "button":
            if io.poll_button(events):
                response_started = response_completed = time.perf_counter()
                break
        else:
            if response_started is None and angular_speed(state) >= GYRO_START_ANGULAR_VELOCITY:
                response_started = time.perf_counter()
                response_state = state
            complete_angle = 30.0 if io.is_mock else GYRO_COMPLETE_ANGLE
            if response_started is not None and angle_displacement(state, neutral) >= complete_angle:
                response_completed = time.perf_counter()
                break

        surface.fill(COLORS["bg"])
        pygame.draw.circle(surface, pygame.Color("white"), surface.get_rect().center, 90)
        draw_text(surface, "지금!", (surface.get_width() // 2, 500), size=42, bold=True, center=True)
        pygame.display.flip()
        clock.tick(60)

    io.turn_off_led()
    io.stop_tone()
    timed_out = response_started is None
    response_started = response_started or time.perf_counter()
    response_completed = response_completed or response_started
    reaction_ms = (response_started - stimulus_time) * 1000
    completion_ms = (response_completed - stimulus_time) * 1000
    delayed = timed_out or reaction_ms > MAX_VALID_RT_MS
    valid = MIN_VALID_RT_MS <= reaction_ms <= MAX_VALID_RT_MS and not timed_out

    if condition == "gyro":
        _wait_for_gyro_return(surface, clock, io, neutral)

    return {
        "trial_index": trial_index,
        "input_condition": condition,
        "random_wait_ms": wait_ms,
        "stimulus_time": round(stimulus_time, 6),
        "response_start_time": round(response_started, 6),
        "response_complete_time": round(response_completed, 6),
        "reaction_time_ms": round(reaction_ms, 1),
        "completion_time_ms": round(completion_ms, 1),
        "gyro_pitch": round(response_state.pitch, 3) if condition == "gyro" else None,
        "gyro_roll": round(response_state.roll, 3) if condition == "gyro" else None,
        "gyro_angular_velocity": round(angular_speed(response_state), 3) if condition == "gyro" else None,
        "early_response": False,
        "delayed_response": delayed,
        "valid": valid,
        "practice": practice,
    }


def run_task1(participant_id: str = "P001", io: BaseModiIO | None = None) -> dict[str, Any]:
    """TASK 1 전체 과정을 실행하고 공통 결과 딕셔너리를 반환한다."""

    owned_io = io is None
    io = io or create_modi_io()
    pygame.init()
    surface = pygame.display.set_mode((960, 640))
    pygame.display.set_caption("TASK 1 - 반응속도와 입력 방식")
    clock = pygame.time.Clock()
    rng = random.Random(str(participant_id))
    trials: list[dict[str, Any]] = []

    try:
        _wait_for_continue(
            surface,
            clock,
            "TASK 1. 반응속도와 입력 방식",
            "빛과 소리가 나오면 버튼 조건에서는 버튼을 누르고, 자이로 조건에서는 손잡이를 한 번 돌립니다.",
        )
        for index, condition in enumerate(PRACTICE_ORDER, start=1):
            _wait_for_continue(
                surface,
                clock,
                f"{condition.upper()} 연습",
                "신호보다 먼저 움직이면 조기 반응입니다. 편안한 시작 자세를 유지하세요.",
            )
            _run_trial(
                surface,
                clock,
                io,
                condition=condition,
                trial_index=index,
                total=len(PRACTICE_ORDER),
                practice=True,
                rng=rng,
            )

        for index, condition in enumerate(TRIAL_ORDER, start=1):
            while True:
                _wait_for_continue(
                    surface,
                    clock,
                    f"시행 {index} / {len(TRIAL_ORDER)} · {condition.upper()}",
                    "가운데 자세를 유지하고 신호를 기다리세요.",
                )
                row = _run_trial(
                    surface,
                    clock,
                    io,
                    condition=condition,
                    trial_index=index,
                    total=len(TRIAL_ORDER),
                    practice=False,
                    rng=rng,
                )
                trials.append(row)
                if not row["early_response"]:
                    break

        button_times = [row["reaction_time_ms"] for row in trials if row["input_condition"] == "button" and row["valid"]]
        gyro_times = [row["reaction_time_ms"] for row in trials if row["input_condition"] == "gyro" and row["valid"]]
        return {
            "task_id": "task1",
            "score": None,
            "metrics": {
                "device_mode": "mock" if io.is_mock else "real",
                "button_median_ms": round(median(button_times), 1) if button_times else None,
                "gyro_median_ms": round(median(gyro_times), 1) if gyro_times else None,
            },
            "trials": trials,
        }
    finally:
        io.turn_off_led()
        io.stop_tone()
        if owned_io:
            io.close()


run_task = run_task1
