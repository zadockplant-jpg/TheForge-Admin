"""Keep SendForge Admin windows inside the usable area of their monitor.

On Windows the usable work area excludes the taskbar and any docked app bars,
so a window placed inside it never hides its title bar or its Save button
behind the taskbar.  Win32 reports coordinates in the calling thread's DPI
awareness, which is also the pixel space Tk uses.

customtkinter multiplies the width and height it is given by its window
scaling (3.0 on a 300 % monitor) but uses the x and y of a geometry string as
raw pixels.  The fitting below works in pixels and converts sizes back to
customtkinter units at the end.
"""

from __future__ import annotations

import ctypes
import math
import sys
from collections.abc import Callable
from tkinter import TclError
from typing import Any, NamedTuple

MARGIN = 4  # logical px kept between a clamped window frame and the work-area edge
_WIN32_ERRORS: tuple[type[BaseException], ...] = (OSError, ValueError, TypeError, ctypes.ArgumentError)


class Rect(NamedTuple):
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def contains(self, other: Rect) -> bool:
        return (
            self.left <= other.left
            and self.top <= other.top
            and other.right <= self.right
            and other.bottom <= self.bottom
        )


NO_FRAME = Rect(0, 0, 0, 0)


class Placement(NamedTuple):
    """Client size, outer-frame position (None: system's choice), and minimum client size."""

    width: int
    height: int
    x: int | None
    y: int | None
    min_width: int
    min_height: int


def _clamp(value: int, low: int, high: int) -> int:
    # When nothing fits, favour the top-left so the title bar stays reachable.
    return low if high < low else max(low, min(value, high))


def fit_to_work_area(
    width: int,
    height: int,
    work: Rect,
    frame: Rect = NO_FRAME,
    *,
    min_width: int = 0,
    min_height: int = 0,
    position: tuple[int, int] | None = None,
    center: bool = True,
    margin: int = MARGIN,
) -> Placement:
    """Fit a window with the preferred client size inside ``work`` (all in pixels).

    ``frame`` is the decoration around the client area (title bar and borders)
    and ``position`` a wanted top-left corner of the outer frame.  A size that
    fits is kept; a larger one shrinks to the work area less ``margin`` on each
    side, and the minimum size shrinks with it so the window can always fit.
    The outer frame then stays inside the work area: ``position`` is clamped,
    otherwise the window is centred, or left to the system when ``center`` is
    false.
    """
    max_width = max(1, work.width - frame.left - frame.right - 2 * margin)
    max_height = max(1, work.height - frame.top - frame.bottom - 2 * margin)
    min_width = max(0, min(min_width, max_width))
    min_height = max(0, min(min_height, max_height))
    width = max(min_width, min(width, max_width))
    height = max(min_height, min(height, max_height))
    if position is None and not center:
        return Placement(width, height, None, None, min_width, min_height)
    outer_width = width + frame.left + frame.right
    outer_height = height + frame.top + frame.bottom
    if position is None:
        x = work.left + (work.width - outer_width) // 2
        y = work.top + (work.height - outer_height) // 2
    else:
        x, y = position
    x = _clamp(x, work.left + margin, work.right - margin - outer_width)
    y = _clamp(y, work.top + margin, work.bottom - margin - outer_height)
    return Placement(width, height, x, y, min_width, min_height)


if sys.platform == "win32":
    from ctypes import wintypes

    class _MonitorInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    # A private handle keeps these argtypes from leaking into customtkinter's ctypes calls.
    _user32 = ctypes.WinDLL("user32")
    _user32.MonitorFromRect.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD]
    _user32.MonitorFromRect.restype = wintypes.HMONITOR
    _user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    _user32.MonitorFromWindow.restype = wintypes.HMONITOR
    _user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MonitorInfo)]
    _user32.GetMonitorInfoW.restype = wintypes.BOOL
    _user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    _user32.GetAncestor.restype = wintypes.HWND
    _user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    _user32.GetWindowRect.restype = wintypes.BOOL
    _user32.AdjustWindowRectEx.argtypes = [ctypes.POINTER(wintypes.RECT), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _user32.AdjustWindowRectEx.restype = wintypes.BOOL

    _MONITOR_DEFAULTTOPRIMARY = 1
    _MONITOR_DEFAULTTONEAREST = 2
    _GA_ROOT = 2
    _WS_OVERLAPPEDWINDOW = 0x00CF0000

    def _rect(value: Any) -> Rect:
        return Rect(value.left, value.top, value.right, value.bottom)

    def _areas(monitor: Any) -> tuple[Rect, Rect] | None:
        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(_MonitorInfo)
        if not monitor or not _user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        return _rect(info.rcMonitor), _rect(info.rcWork)

    def _frame_window(window: Any) -> Any:
        """The top-level frame Windows draws around a Tk toplevel's client area."""
        return _user32.GetAncestor(window.winfo_id(), _GA_ROOT)

    def _outer_rect(window: Any) -> Rect | None:
        box = wintypes.RECT()
        hwnd = _frame_window(window)
        if not hwnd or not _user32.GetWindowRect(hwnd, ctypes.byref(box)):
            return None
        return _rect(box)


def _window_scaling(window: Any) -> float:
    """customtkinter's size multiplier for ``window``; 1 for plain Tk windows."""
    getter = getattr(window, "_get_window_scaling", None)
    try:
        scale = float(getter()) if getter else 1.0
    except (TypeError, ValueError, TclError):
        scale = 1.0
    return scale if scale > 0 else 1.0


def _to_units(pixels: int, scale: float) -> int:
    # Round down so customtkinter's multiply-back never exceeds the fitted pixels.
    return max(0, math.floor(pixels / scale + 1e-9))


def _scaled_margin(window: Any) -> int:
    try:
        return max(1, round(MARGIN * window.winfo_fpixels("1i") / 96))
    except TclError:
        return MARGIN


def monitor_and_work_area(window: Any, *, near: Rect | None = None, parent: Any = None) -> tuple[Rect, Rect]:
    """The (monitor, work area) rectangles a window should fit inside, in Tk pixels.

    Windows picks the monitor showing ``parent``, else the one nearest ``near``
    (an outer window rectangle), else the primary monitor.  Other platforms
    return the whole screen for both.
    """
    if sys.platform == "win32":
        try:
            if parent is not None and parent.winfo_ismapped():
                monitor = _user32.MonitorFromWindow(_frame_window(parent), _MONITOR_DEFAULTTONEAREST)
            elif near is not None:
                monitor = _user32.MonitorFromRect(ctypes.byref(wintypes.RECT(*near)), _MONITOR_DEFAULTTONEAREST)
            else:
                monitor = _user32.MonitorFromRect(ctypes.byref(wintypes.RECT(0, 0, 1, 1)), _MONITOR_DEFAULTTOPRIMARY)
            areas = _areas(monitor)
            if areas:
                return areas
        except (*_WIN32_ERRORS, TclError):
            pass
    screen = Rect(0, 0, window.winfo_screenwidth(), window.winfo_screenheight())
    return screen, screen


def _measured_frame(window: Any) -> Rect | None:
    try:
        if not window.winfo_ismapped():
            return None
        outer = _outer_rect(window)
        if outer is None:
            return None
        left, top = window.winfo_rootx() - outer.left, window.winfo_rooty() - outer.top
        right = outer.right - window.winfo_rootx() - window.winfo_width()
        bottom = outer.bottom - window.winfo_rooty() - window.winfo_height()
    except (*_WIN32_ERRORS, TclError):
        return None
    frame = Rect(left, top, right, bottom)
    return frame if all(0 <= side < 400 for side in frame) else None


def frame_extents(window: Any) -> Rect:
    """Title bar and border thickness around a window's client area, in Tk pixels.

    Measured from the real frame once the window is shown, before that the
    standard frame of a resizable window.  Off Windows the window manager's
    decoration is unknown until mapped, so it counts as zero.
    """
    if sys.platform != "win32":
        return NO_FRAME
    measured = _measured_frame(window)
    if measured is not None:
        return measured
    box = wintypes.RECT(0, 0, 0, 0)
    try:
        if _user32.AdjustWindowRectEx(ctypes.byref(box), _WS_OVERLAPPEDWINDOW, False, 0):
            return Rect(-box.left, -box.top, box.right, box.bottom)
    except _WIN32_ERRORS:
        pass
    scale = window.winfo_fpixels("1i") / 96
    return Rect(*(round(side * scale) for side in (8, 31, 8, 8)))


def after_first_map(window: Any, callback: Callable[[], None]) -> None:
    """Run ``callback`` once, just after ``window`` first appears on screen."""
    pending = [True]

    def on_map(event: Any) -> None:
        # Toplevel bindings also see their children's events; react to the window itself.
        if event.widget is window and pending:
            pending.clear()
            window.after_idle(callback)

    window.bind("<Map>", on_map, add="+")


def _apply(window: Any, placement: Placement, scale: float, *, set_minimum: bool) -> None:
    if set_minimum:
        window.minsize(_to_units(placement.min_width, scale), _to_units(placement.min_height, scale))
    size = f"{_to_units(placement.width, scale)}x{_to_units(placement.height, scale)}"
    if placement.x is None or placement.y is None:
        window.geometry(size)
    else:
        window.geometry(f"{size}+{placement.x}+{placement.y}")


def keep_inside_work_area(window: Any, *, min_width: int = 0, min_height: int = 0) -> None:
    """Pull a shown window back inside the work area of the monitor it landed on.

    The minimums are in the window's own units.  A no-op when the window
    already fits, is maximized or minimized, or when the platform cannot report
    a work area.
    """
    if sys.platform != "win32":
        return
    try:
        if window.wm_state() != "normal":
            return
    except TclError:
        return
    frame = _measured_frame(window)
    try:
        outer = _outer_rect(window) if frame is not None else None
        areas = _areas(_user32.MonitorFromWindow(_frame_window(window), _MONITOR_DEFAULTTONEAREST)) if outer else None
    except (*_WIN32_ERRORS, TclError):
        return
    if frame is None or outer is None or areas is None or areas[1].contains(outer):
        return
    scale = _window_scaling(window)
    try:
        placement = fit_to_work_area(
            window.winfo_width(),
            window.winfo_height(),
            areas[1],
            frame,
            min_width=round(min_width * scale),
            min_height=round(min_height * scale),
            position=(outer.left, outer.top),
            margin=_scaled_margin(window),
        )
        _apply(window, placement, scale, set_minimum=bool(min_width or min_height))
    except TclError:
        pass  # the window closed before it could be moved


def place_window(
    window: Any,
    width: int,
    height: int,
    *,
    min_width: int = 0,
    min_height: int = 0,
    parent: Any = None,
    center: bool = True,
) -> None:
    """Size and position a window so its whole frame fits the work area.

    Sizes are in the window's own units, the same numbers its ``geometry`` and
    ``minsize`` take.  A dialog with a shown ``parent`` is centred over the
    parent's window on that monitor.  Once the window is shown its real frame
    and monitor are checked again, in case the system moved or decorated it
    differently than estimated.
    """
    scale = _window_scaling(window)
    frame = frame_extents(window)
    width_px, height_px = round(width * scale), round(height * scale)
    owner = None
    position = None
    try:
        if parent is not None and parent.winfo_toplevel().winfo_ismapped():
            owner = parent.winfo_toplevel()
            position = (
                owner.winfo_rootx() + (owner.winfo_width() - width_px - frame.left - frame.right) // 2,
                owner.winfo_rooty() + (owner.winfo_height() - height_px - frame.top - frame.bottom) // 2,
            )
    except TclError:
        owner = position = None
    _monitor, work = monitor_and_work_area(window, parent=owner)
    placement = fit_to_work_area(
        width_px,
        height_px,
        work,
        frame,
        min_width=round(min_width * scale),
        min_height=round(min_height * scale),
        position=position,
        center=center,
        margin=_scaled_margin(window),
    )
    _apply(window, placement, scale, set_minimum=bool(min_width or min_height))
    after_first_map(window, lambda: keep_inside_work_area(window, min_width=min_width, min_height=min_height))
