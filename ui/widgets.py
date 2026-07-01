"""pygame 화면에서 재사용하는 버튼, 입력창과 텍스트 도구를 제공한다."""

from __future__ import annotations

import re
from typing import Callable, Iterable

import pygame

from config import (
    COLOR_BG,
    COLOR_ERROR,
    COLOR_HIGHLIGHT,
    COLOR_MUTED,
    COLOR_PANEL,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_TEXT,
)


COLORS = {
    "bg": pygame.Color(COLOR_BG),
    "panel": pygame.Color(COLOR_PANEL),
    "primary": pygame.Color(COLOR_PRIMARY),
    "primary_hover": pygame.Color(COLOR_PRIMARY_HOVER),
    "secondary": pygame.Color(COLOR_SECONDARY),
    "text": pygame.Color(COLOR_TEXT),
    "muted": pygame.Color(COLOR_MUTED),
    "error": pygame.Color(COLOR_ERROR),
    "success": pygame.Color(COLOR_SUCCESS),
    "highlight": pygame.Color(COLOR_HIGHLIGHT),
}

_FONT_NAMES = ("malgungothic", "nanumgothic", "notosanscjkk", "arial")
_font_cache: dict[tuple[int, bool], pygame.font.Font] = {}
_ID_PATTERN = re.compile(r"^[가-힣A-Za-z0-9_-]+$")


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """사용 가능한 한글 글꼴을 찾아 캐시된 pygame Font를 반환한다."""

    key = (size, bold)
    cached = _font_cache.get(key)
    try:
        cache_is_valid = cached is not None and cached.size("M")[0] > 0
    except pygame.error:
        cache_is_valid = False
    if not cache_is_valid:
        match = pygame.font.match_font(_FONT_NAMES, bold=bold)
        _font_cache[key] = pygame.font.Font(match, size)
    return _font_cache[key]


def draw_text(
    surface: pygame.Surface,
    text: object,
    position: tuple[int, int],
    *,
    size: int = 24,
    color: pygame.Color | None = None,
    bold: bool = False,
    center: bool = False,
) -> pygame.Rect:
    """텍스트를 그리고 실제 표시 영역을 반환한다."""

    rendered = get_font(size, bold).render(str(text), True, color or COLORS["text"])
    rect = rendered.get_rect(center=position) if center else rendered.get_rect(topleft=position)
    surface.blit(rendered, rect)
    return rect


def draw_wrapped_text(
    surface: pygame.Surface,
    text: str,
    rect: pygame.Rect,
    *,
    size: int = 22,
    color: pygame.Color | None = None,
    line_gap: int = 8,
) -> int:
    """지정된 폭에 맞춰 여러 줄 텍스트를 그리고 마지막 y 좌표를 반환한다."""

    font = get_font(size)
    y = rect.y
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split(" ")
        line = ""
        lines: list[str] = []
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if font.size(candidate)[0] <= rect.width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
        for value in lines:
            rendered = font.render(value, True, color or COLORS["text"])
            surface.blit(rendered, (rect.x, y))
            y += font.get_linesize() + line_gap
    return y


def validate_id_format(raw_id: str) -> tuple[bool, str]:
    """UI 입력 단계에서 참가자 ID의 기본 형식을 검사한다."""

    value = str(raw_id).strip()
    if not value:
        return False, "ID를 입력해 주세요."
    if not 2 <= len(value) <= 16:
        return False, "ID는 2~16자로 입력해 주세요."
    if not _ID_PATTERN.fullmatch(value):
        return False, "한글, 영문, 숫자, _, -만 사용할 수 있습니다."
    return True, ""


class Button:
    """마우스와 키보드 포커스를 지원하는 pygame 버튼이다."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        text: str,
        callback: Callable[[], None],
        *,
        primary: bool = True,
        enabled: bool = True,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.primary = primary
        self.enabled = enabled

    def handle_event(self, event: pygame.event.Event) -> bool:
        if (
            self.enabled
            and event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        hovered = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())
        if not self.enabled:
            color = COLORS["secondary"]
        elif self.primary:
            color = COLORS["primary_hover"] if hovered else COLORS["primary"]
        else:
            color = COLORS["highlight"] if hovered else COLORS["secondary"]
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        draw_text(
            surface,
            self.text,
            self.rect.center,
            size=22,
            bold=self.primary,
            center=True,
            color=COLORS["text"] if self.enabled else COLORS["muted"],
        )


class TextInput:
    """한글을 포함한 pygame TEXTINPUT 기반 한 줄 입력창이다."""

    def __init__(
        self,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        placeholder: str = "",
        max_length: int = 16,
        on_submit: Callable[[str], None] | None = None,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.max_length = max_length
        self.on_submit = on_submit
        self.value = ""
        self.active = False

    def focus(self) -> None:
        self.active = True
        pygame.key.start_text_input()

    def blur(self) -> None:
        self.active = False
        pygame.key.stop_text_input()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.focus()
            else:
                self.blur()
            return self.active
        if not self.active:
            return False
        if event.type == pygame.TEXTINPUT:
            remaining = self.max_length - len(self.value)
            self.value += event.text[: max(0, remaining)]
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.on_submit:
                    self.on_submit(self.value.strip())
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COLORS["panel"], self.rect, border_radius=10)
        border = COLORS["primary"] if self.active else COLORS["secondary"]
        pygame.draw.rect(surface, border, self.rect, width=2, border_radius=10)
        shown = self.value or self.placeholder
        color = COLORS["text"] if self.value else COLORS["muted"]
        draw_text(surface, shown, (self.rect.x + 16, self.rect.y + 15), size=24, color=color)


def draw_metric_rows(
    surface: pygame.Surface,
    rows: Iterable[tuple[str, object]],
    rect: pygame.Rect,
) -> None:
    """결과 이름과 값을 정렬된 행으로 표시한다."""

    pygame.draw.rect(surface, COLORS["panel"], rect, border_radius=14)
    y = rect.y + 18
    for label, value in rows:
        draw_text(surface, label, (rect.x + 22, y), size=20, color=COLORS["muted"])
        rendered = get_font(21, True).render(str(value), True, COLORS["text"])
        surface.blit(rendered, (rect.right - rendered.get_width() - 22, y))
        y += 42
