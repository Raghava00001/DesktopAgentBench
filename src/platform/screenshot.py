"""
Screenshot capture utilities for DesktopAgentBench.

Provides fast screenshot capture using PIL ImageGrab with optional
Win32 BitBlt fallback for performance-critical paths.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def capture_screen(
    region: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """
    Capture the current screen contents.

    Args:
        region: Optional (left, top, right, bottom) to capture a subregion.
                None captures the full primary screen.

    Returns:
        PIL Image of the captured region.
    """
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=region)
        return img
    except Exception as e:
        logger.warning(f"PIL ImageGrab failed: {e}, using fallback")
        return _fallback_capture(region)


def capture_window(hwnd: int) -> Image.Image:
    """
    Capture the contents of a specific window by its handle.

    Falls back to full-screen capture if window capture fails.
    """
    try:
        import ctypes
        import ctypes.wintypes

        user32 = ctypes.windll.user32
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))

        from PIL import ImageGrab
        return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    except Exception as e:
        logger.warning(f"Window capture failed for hwnd={hwnd}: {e}")
        return capture_screen()


def save_screenshot(
    image: Image.Image,
    path: Path | str,
    format: str = "PNG",
    quality: int = 85,
) -> Path:
    """
    Save a screenshot to disk.

    Args:
        image: PIL Image to save.
        path: Output file path.
        format: Image format (PNG, JPEG, WebP).
        quality: JPEG/WebP quality (1-100).

    Returns:
        Path to the saved file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    save_kwargs: dict = {"format": format}
    if format.upper() in ("JPEG", "WEBP"):
        save_kwargs["quality"] = quality

    image.save(str(path), **save_kwargs)
    return path


def capture_and_save(
    path: Path | str,
    region: tuple[int, int, int, int] | None = None,
    format: str = "PNG",
) -> tuple[Image.Image, Path]:
    """Capture the screen and save to a file in one call."""
    img = capture_screen(region)
    saved = save_screenshot(img, path, format)
    return img, saved


def _fallback_capture(
    region: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """
    Fallback screenshot using Win32 BitBlt.

    Used when PIL's ImageGrab is unavailable or fails.
    """
    try:
        import ctypes

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        if region:
            left, top, right, bottom = region
            width = right - left
            height = bottom - top
        else:
            left, top = 0, 0
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)

        hdc_screen = user32.GetDC(None)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        gdi32.SelectObject(hdc_mem, hbmp)
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, left, top, 0x00CC0020)

        # Convert to PIL Image
        from ctypes import wintypes
        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = width
        bmi.biHeight = -height  # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer_size = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_size)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, height, buffer, ctypes.byref(bmi), 0)

        img = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)

        # Cleanup
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)

        return img.convert("RGB")

    except Exception as e:
        logger.error(f"BitBlt screenshot fallback also failed: {e}")
        return Image.new("RGB", (1920, 1080), color=(0, 0, 0))
