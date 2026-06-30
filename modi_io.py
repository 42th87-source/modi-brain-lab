"""실제 MODI 모듈과 키보드 기반 모의 장치에 공통 입출력 인터페이스를 제공한다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pygame


@dataclass(slots=True)
class GyroState:
    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    angular_velocity_x: float = 0.0
    angular_velocity_y: float = 0.0
    angular_velocity_z: float = 0.0


class BaseModiIO:
    """TASK 코드가 실제·모의 장치에 공통으로 사용하는 메서드를 정의한다."""

    is_mock = False

    def poll_button(self, events: Iterable[pygame.event.Event] = ()) -> bool:
        raise NotImplementedError

    def get_dial_value(self) -> float:
        raise NotImplementedError

    def get_gyro(self) -> GyroState:
        raise NotImplementedError

    def set_led(self, red: int, green: int, blue: int) -> None:
        raise NotImplementedError

    def turn_off_led(self) -> None:
        self.set_led(0, 0, 0)

    def play_tone(self, frequency: int, volume: int = 60) -> None:
        raise NotImplementedError

    def stop_tone(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        self.turn_off_led()
        self.stop_tone()


class MockModiIO(BaseModiIO):
    """스페이스·방향키를 MODI 버튼과 자이로 대신 사용하는 개발용 장치다."""

    is_mock = True

    def __init__(self) -> None:
        self._dial = 0.0
        self.led = (0, 0, 0)
        self.tone = (0, 0)
        self._tone_channel: pygame.mixer.Channel | None = None

    def poll_button(self, events: Iterable[pygame.event.Event] = ()) -> bool:
        return any(
            event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN)
            for event in events
        )

    def get_dial_value(self) -> float:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self._dial = max(0.0, self._dial - 1.5)
        if keys[pygame.K_RIGHT]:
            self._dial = min(100.0, self._dial + 1.5)
        return self._dial

    def get_gyro(self) -> GyroState:
        keys = pygame.key.get_pressed()
        roll = 0.0
        pitch = 0.0
        if keys[pygame.K_LEFT]:
            roll -= 35.0
        if keys[pygame.K_RIGHT]:
            roll += 35.0
        if keys[pygame.K_UP]:
            pitch -= 35.0
        if keys[pygame.K_DOWN]:
            pitch += 35.0
        return GyroState(pitch=pitch, roll=roll)

    def set_led(self, red: int, green: int, blue: int) -> None:
        self.led = (int(red), int(green), int(blue))

    def play_tone(self, frequency: int, volume: int = 60) -> None:
        self.tone = (int(frequency), int(volume))
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=44_100, size=-16, channels=2)
            sample_rate = int(pygame.mixer.get_init()[0])
            times = np.arange(int(sample_rate * 0.15)) / sample_rate
            wave = np.sin(2 * np.pi * frequency * times) * (volume / 100) * 16_000
            stereo = np.column_stack((wave, wave)).astype(np.int16)
            sound = pygame.sndarray.make_sound(stereo)
            self._tone_channel = sound.play(loops=-1)
        except (pygame.error, ValueError):
            self._tone_channel = None

    def stop_tone(self) -> None:
        if self._tone_channel is not None:
            self._tone_channel.stop()
            self._tone_channel = None
        self.tone = (0, 0)


class RealModiIO(BaseModiIO):
    """pymodi-plus의 MODI 번들을 안전한 공통 메서드로 감싼다."""

    def __init__(self, bundle: Any | None = None) -> None:
        if bundle is None:
            import modi

            bundle = modi.MODI()
        self.bundle = bundle
        self.button = self._first("buttons")
        self.dial = self._first("dials")
        self.gyro = self._first("gyros")
        self.led = self._first("leds")
        self.speaker = self._first("speakers")
        self._last_button = False

    def _first(self, collection_name: str) -> Any:
        collection = getattr(self.bundle, collection_name, None)
        return collection[0] if collection else None

    def module_status(self) -> dict[str, bool]:
        return {
            "button": self.button is not None,
            "dial": self.dial is not None,
            "gyro": self.gyro is not None,
            "led": self.led is not None,
            "speaker": self.speaker is not None,
        }

    def poll_button(self, events: Iterable[pygame.event.Event] = ()) -> bool:
        if self.button is None:
            return False
        current = bool(getattr(self.button, "pressed", False))
        clicked = bool(getattr(self.button, "clicked", False))
        rising = current and not self._last_button
        self._last_button = current
        return clicked or rising

    def get_dial_value(self) -> float:
        if self.dial is None:
            return 0.0
        return float(getattr(self.dial, "degree", 0.0))

    def get_gyro(self) -> GyroState:
        if self.gyro is None:
            return GyroState()
        return GyroState(
            pitch=float(getattr(self.gyro, "pitch", 0.0)),
            roll=float(getattr(self.gyro, "roll", 0.0)),
            yaw=float(getattr(self.gyro, "yaw", 0.0)),
            angular_velocity_x=float(getattr(self.gyro, "angular_vel_x", 0.0)),
            angular_velocity_y=float(getattr(self.gyro, "angular_vel_y", 0.0)),
            angular_velocity_z=float(getattr(self.gyro, "angular_vel_z", 0.0)),
        )

    def set_led(self, red: int, green: int, blue: int) -> None:
        if self.led is not None:
            self.led.rgb = tuple(max(0, min(100, int(value))) for value in (red, green, blue))

    def play_tone(self, frequency: int, volume: int = 60) -> None:
        if self.speaker is not None:
            self.speaker.tune = int(frequency), max(0, min(100, int(volume)))

    def stop_tone(self) -> None:
        if self.speaker is not None:
            turn_off = getattr(self.speaker, "turn_off", None)
            if callable(turn_off):
                turn_off()
            else:
                self.speaker.volume = 0

    def close(self) -> None:
        super().close()
        close = getattr(self.bundle, "close", None)
        if callable(close):
            close()


def create_modi_io(*, force_mock: bool | None = None) -> BaseModiIO:
    """환경 설정에 따라 실제 MODI에 연결하고 실패하면 모의 장치를 반환한다."""

    if force_mock is None:
        force_mock = os.environ.get("MODI_MOCK", "0") == "1"
    if force_mock:
        return MockModiIO()
    try:
        return RealModiIO()
    except Exception as error:
        print(f"[MODI] 실제 장치 연결 실패, 모의 모드로 전환합니다: {error}")
        return MockModiIO()
