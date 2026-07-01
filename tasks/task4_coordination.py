"""자이로 커서와 비트 버튼을 함께 사용하는 TASK 4를 실행한다."""

from __future__ import annotations

import math
import time
from typing import Any

import pygame

from modi_io import BaseModiIO, GyroState, create_modi_io
from ui.widgets import COLORS, create_display, draw_text, draw_wrapped_text


BEAT_INTERVAL_MS = 750
VALID_BEAT_WINDOW_MS = 400
TARGET_RADIUS = 72
CURSOR_RADIUS = 20
GYRO_SCALE = 7.0
TARGET_CYCLE_S = 10.0
TARGET_WAYPOINTS = (
    (-120, 0),
    (85, 0),
    (-45, 0),
    (135, 0),
    (-130, 0),
    (40, 0),
    (115, 0),
    (-80, 0),
)
TARGET_SEGMENT_DURATIONS = (1.4, 1.0, 1.7, 1.2, 1.5, 0.9, 1.3, 1.0)


def target_position(elapsed_s: float, width: int, height: int) -> tuple[int, int]:
    """속도와 방향이 달라지는 10초 고정 경로 위의 목표 위치를 반환한다."""

    cycle_time = elapsed_s % TARGET_CYCLE_S
    accumulated = 0.0
    for index, duration in enumerate(TARGET_SEGMENT_DURATIONS):
        if cycle_time < accumulated + duration:
            progress = (cycle_time - accumulated) / duration
            # 급격한 방향 전환은 유지하되 구간 안에서는 부드럽게 이동한다.
            eased = progress * progress * (3.0 - 2.0 * progress)
            start_x, start_y = TARGET_WAYPOINTS[index]
            end_x, end_y = TARGET_WAYPOINTS[(index + 1) % len(TARGET_WAYPOINTS)]
            offset_x = start_x + (end_x - start_x) * eased
            offset_y = start_y + (end_y - start_y) * eased
            return round(width / 2 + offset_x), round(height / 2 + offset_y)
        accumulated += duration
    start_x, start_y = TARGET_WAYPOINTS[0]
    return round(width / 2 + start_x), round(height / 2 + start_y)


def _wait_for_start(surface: pygame.Surface, clock: pygame.time.Clock, io: BaseModiIO, title: str, detail: str) -> None:
    while True:
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        if any(event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE) for event in events):
            return
        if io.poll_button(events):
            return
        surface.fill(COLORS["bg"])
        draw_text(surface, title, (surface.get_width() // 2, 220), size=34, bold=True, center=True)
        draw_wrapped_text(surface, detail, pygame.Rect(170, 285, 620, 100), size=22, color=COLORS["muted"])
        draw_text(surface, "MODI 버튼을 누르면 시작합니다.", (surface.get_width() // 2, 440), size=21, center=True)
        pygame.display.flip()
        clock.tick(60)


def _show_phase(surface: pygame.Surface, clock: pygame.time.Clock, title: str, detail: str) -> None:
    """추가 입력 없이 다음 단계 안내를 잠시 보여준다."""

    started = time.perf_counter()
    while time.perf_counter() - started < 1.1:
        if any(event.type == pygame.QUIT for event in pygame.event.get()):
            raise KeyboardInterrupt
        surface.fill(COLORS["bg"])
        draw_text(surface, title, (surface.get_width() // 2, 245), size=34, bold=True, center=True)
        draw_wrapped_text(surface, detail, pygame.Rect(170, 315, 620, 90), size=22, color=COLORS["muted"])
        draw_text(surface, "곧 자동으로 시작합니다.", (surface.get_width() // 2, 465), size=20, center=True)
        pygame.display.flip()
        clock.tick(60)


def _run_phase(
    surface: pygame.Surface,
    clock: pygame.time.Clock,
    io: BaseModiIO,
    phase: str,
    duration_s: float,
    neutral: GyroState,
    *,
    cursor_enabled: bool,
    rhythm_enabled: bool,
) -> list[dict[str, Any]]:
    started = time.perf_counter()
    last_sample = -1.0
    beat_times: list[float] = []
    presses: list[float] = []
    rows: list[dict[str, Any]] = []
    next_beat = 0.75 if rhythm_enabled else math.inf
    tone_off_at = math.inf
    cursor_x = surface.get_width() / 2
    while True:
        now = time.perf_counter()
        elapsed = now - started
        if elapsed >= duration_s:
            break
        events = pygame.event.get()
        if any(event.type == pygame.QUIT for event in events):
            raise KeyboardInterrupt
        if io.poll_button(events):
            presses.append(elapsed)
            io.turn_off_led()
        if rhythm_enabled and elapsed >= next_beat:
            beat_times.append(next_beat)
            io.play_tone(1300, 90)
            tone_off_at = elapsed + 0.35
            next_beat += BEAT_INTERVAL_MS / 1000
        if elapsed >= tone_off_at:
            io.stop_tone()
            tone_off_at = math.inf

        gyro = io.get_gyro()
        roll_delta = gyro.roll - neutral.roll
        pitch_delta = gyro.pitch - neutral.pitch
        control_delta = roll_delta if abs(roll_delta) >= abs(pitch_delta) else pitch_delta
        raw_cursor_x = surface.get_width() / 2 + control_delta * GYRO_SCALE
        cursor_x += (raw_cursor_x - cursor_x) * 0.28
        cursor_y = surface.get_height() / 2
        cursor_x = max(CURSOR_RADIUS, min(surface.get_width() - CURSOR_RADIUS, cursor_x))
        cursor_y = max(CURSOR_RADIUS, min(surface.get_height() - CURSOR_RADIUS, cursor_y))
        target_x, target_y = target_position(elapsed, surface.get_width(), surface.get_height())
        distance = abs(cursor_x - target_x)
        if cursor_enabled and elapsed - last_sample >= 1 / 30:
            rows.append({
                "phase": phase,
                "sample_time": round(elapsed, 4),
                "gyro_pitch": round(gyro.pitch, 3),
                "gyro_roll": round(gyro.roll, 3),
                "cursor_x": round(cursor_x, 2),
                "cursor_y": round(cursor_y, 2),
                "target_x": target_x,
                "target_y": target_y,
                "distance_from_target": round(distance, 2),
                "inside_target": distance <= TARGET_RADIUS,
            })
            last_sample = elapsed

        surface.fill(COLORS["bg"])
        draw_text(surface, f"남은 시간 {max(0, duration_s - elapsed):.1f}초", (30, 28), size=20, color=COLORS["muted"])
        if cursor_enabled:
            pygame.draw.circle(surface, pygame.Color("#F6C453"), (target_x, target_y), TARGET_RADIUS, width=12)
            draw_text(surface, "목표 영역", (target_x, target_y - TARGET_RADIUS - 28), size=18, color=pygame.Color("#F6C453"), center=True)
            pygame.draw.circle(surface, COLORS["primary"], (int(cursor_x), int(cursor_y)), CURSOR_RADIUS)
            pygame.draw.circle(surface, pygame.Color("white"), (int(cursor_x), int(cursor_y)), CURSOR_RADIUS, width=3)
            draw_text(surface, "내 커서", (int(cursor_x), int(cursor_y) + 42), size=17, color=pygame.Color("white"), center=True)
            draw_text(surface, "손잡이를 좌우로 돌려 파란 커서를 노란 목표 안에 유지하세요", (surface.get_width() // 2, surface.get_height() - 48), size=20, color=COLORS["muted"], center=True)
        if rhythm_enabled:
            draw_text(surface, "비트에 맞춰 버튼", (surface.get_width() // 2, 90), size=24, center=True)
        pygame.display.flip()
        clock.tick(60)
    io.stop_tone()

    unmatched = set(range(len(presses)))
    for beat_index, beat_time in enumerate(beat_times, start=1):
        candidates = [(abs(presses[index] - beat_time), index) for index in unmatched]
        best = min(candidates, default=None)
        matched_index = best[1] if best and best[0] * 1000 <= VALID_BEAT_WINDOW_MS else None
        if matched_index is not None:
            unmatched.remove(matched_index)
        button_time = presses[matched_index] if matched_index is not None else None
        rows.append({
            "phase": phase,
            "beat_index": beat_index,
            "beat_time": round(beat_time, 4),
            "button_time": round(button_time, 4) if button_time is not None else None,
            "beat_error_ms": round((button_time - beat_time) * 1000, 1) if button_time is not None else None,
            "missed_beat": button_time is None,
            "extra_press": False,
        })
    for press_index in unmatched:
        rows.append({"phase": phase, "button_time": round(presses[press_index], 4), "extra_press": True, "missed_beat": False})
    return rows


def run_task4(participant_id: str = "P001", io: BaseModiIO | None = None) -> dict[str, Any]:
    """단독 기준과 이중 과제를 실행하고 공통 결과 딕셔너리를 반환한다."""

    owned_io = io is None
    io = io or create_modi_io()
    pygame.init()
    surface = create_display((960, 640))
    pygame.display.set_caption("TASK 4 - 운동 협응")
    clock = pygame.time.Clock()
    _wait_for_start(surface, clock, io, "TASK 4. 협응과 이중 과제", "손잡이를 좌우로 돌려 파란 커서를 움직입니다. 노란 원이 목표 영역입니다. 소리가 나면 버튼을 누르세요.")
    neutral = io.get_gyro()
    try:
        _show_phase(surface, clock, "손잡이 연습", "파란 내 커서를 노란 목표 영역 안에 넣어 보세요.")
        _run_phase(surface, clock, io, "practice_cursor", 4.0, neutral, cursor_enabled=True, rhythm_enabled=False)
        _show_phase(surface, clock, "리듬 연습", "짧은 소리가 날 때마다 버튼을 한 번 누르세요.")
        _run_phase(surface, clock, io, "practice_rhythm", 3.0, neutral, cursor_enabled=False, rhythm_enabled=True)
        neutral = io.get_gyro()
        _show_phase(surface, clock, "커서 단독", "8초 동안 파란 커서를 노란 목표 안에 유지하세요.")
        rows = _run_phase(surface, clock, io, "cursor_baseline", 8.0, neutral, cursor_enabled=True, rhythm_enabled=False)
        _show_phase(surface, clock, "리듬 단독", "소리가 날 때마다 버튼을 한 번 누르세요.")
        rows += _run_phase(surface, clock, io, "rhythm_baseline", 4.5, neutral, cursor_enabled=False, rhythm_enabled=True)
        _show_phase(surface, clock, "동시 수행", "목표를 따라가면서 소리가 날 때 버튼도 누르세요.")
        rows += _run_phase(surface, clock, io, "dual_task", 12.0, neutral, cursor_enabled=True, rhythm_enabled=True)
        return {
            "task_id": "task4",
            "score": None,
            "metrics": {
                "device_mode": "mock" if io.is_mock else "real",
                "calibration_pitch": neutral.pitch,
                "calibration_roll": neutral.roll,
            },
            "trials": rows,
        }
    finally:
        if owned_io:
            io.close()


run_task = run_task4
