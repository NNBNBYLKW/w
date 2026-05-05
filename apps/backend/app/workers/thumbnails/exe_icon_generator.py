import ctypes
import os
from pathlib import Path

from PIL import Image


class ExeIconGenerationError(RuntimeError):
    pass


class ExeIconGeneratorWorker:
    def generate_icon(self, source_path: Path, output_path: Path, *, size: int = 64) -> None:
        if not self._is_windows():
            raise ExeIconGenerationError("Executable icon extraction is only available on Windows.")
        if not source_path.exists():
            raise ExeIconGenerationError("Executable file does not exist.")

        temporary_path = output_path.with_name(f".{output_path.stem}.tmp.png")
        if temporary_path.exists():
            temporary_path.unlink()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        icon_handle = self._extract_icon(source_path)
        try:
            image = self._render_icon_to_image(icon_handle, size=size)
            image.save(temporary_path, format="PNG")
            temporary_path.replace(output_path)
        except OSError as error:
            if temporary_path.exists():
                temporary_path.unlink()
            raise ExeIconGenerationError("Executable icon could not be written.") from error
        finally:
            ctypes.windll.user32.DestroyIcon(icon_handle)

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise ExeIconGenerationError("Executable icon output file was not created.")

    def is_expected_generation_failure(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
                ExeIconGenerationError,
            ),
        )

    def _is_windows(self) -> bool:
        return os.name == "nt"

    def _extract_icon(self, source_path: Path):
        shell32 = ctypes.windll.shell32
        shfileinfo = SHFILEINFOW()
        result = shell32.SHGetFileInfoW(
            str(source_path),
            0,
            ctypes.byref(shfileinfo),
            ctypes.sizeof(shfileinfo),
            SHGFI_ICON | SHGFI_LARGEICON,
        )
        if result == 0 or not shfileinfo.hIcon:
            raise ExeIconGenerationError("Windows Shell did not return an executable icon.")
        return shfileinfo.hIcon

    def _render_icon_to_image(self, icon_handle, *, size: int) -> Image.Image:
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        screen_dc = user32.GetDC(None)
        if not screen_dc:
            raise ExeIconGenerationError("Could not get screen device context.")

        memory_dc = None
        bitmap_handle = None
        old_object = None
        bits_pointer = ctypes.c_void_p()

        try:
            memory_dc = gdi32.CreateCompatibleDC(screen_dc)
            if not memory_dc:
                raise ExeIconGenerationError("Could not create icon drawing context.")

            bitmap_info = BITMAPINFO()
            bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bitmap_info.bmiHeader.biWidth = size
            # Negative height creates a top-down DIB, which maps directly to Pillow rows.
            bitmap_info.bmiHeader.biHeight = -size
            bitmap_info.bmiHeader.biPlanes = 1
            bitmap_info.bmiHeader.biBitCount = 32
            bitmap_info.bmiHeader.biCompression = BI_RGB

            bitmap_handle = gdi32.CreateDIBSection(
                memory_dc,
                ctypes.byref(bitmap_info),
                DIB_RGB_COLORS,
                ctypes.byref(bits_pointer),
                None,
                0,
            )
            if not bitmap_handle or not bits_pointer:
                raise ExeIconGenerationError("Could not create icon bitmap.")

            old_object = gdi32.SelectObject(memory_dc, bitmap_handle)
            draw_result = user32.DrawIconEx(memory_dc, 0, 0, icon_handle, size, size, 0, None, DI_NORMAL)
            if draw_result == 0:
                raise ExeIconGenerationError("Could not draw executable icon.")

            buffer_size = size * size * 4
            raw_bytes = ctypes.string_at(bits_pointer, buffer_size)
            return Image.frombuffer("RGBA", (size, size), raw_bytes, "raw", "BGRA", 0, 1).copy()
        finally:
            if memory_dc and old_object:
                gdi32.SelectObject(memory_dc, old_object)
            if bitmap_handle:
                gdi32.DeleteObject(bitmap_handle)
            if memory_dc:
                gdi32.DeleteDC(memory_dc)
            user32.ReleaseDC(None, screen_dc)


MAX_PATH = 260
SHGFI_ICON = 0x000000100
SHGFI_LARGEICON = 0x000000000
DI_NORMAL = 0x0003
BI_RGB = 0
DIB_RGB_COLORS = 0


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [
        ("hIcon", ctypes.c_void_p),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", ctypes.c_uint32),
        ("szDisplayName", ctypes.c_wchar * MAX_PATH),
        ("szTypeName", ctypes.c_wchar * 80),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class RGBQUAD(ctypes.Structure):
    _fields_ = [
        ("rgbBlue", ctypes.c_ubyte),
        ("rgbGreen", ctypes.c_ubyte),
        ("rgbRed", ctypes.c_ubyte),
        ("rgbReserved", ctypes.c_ubyte),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", RGBQUAD * 1),
    ]
