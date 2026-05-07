import ctypes
import os
from pathlib import Path

from PIL import Image


class ExeIconGenerationError(RuntimeError):
    pass


class ExeIconGeneratorWorker:
    def generate_icon(self, source_path: Path, output_path: Path, *, size: int = 256) -> None:
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
            image = self.normalize_icon_canvas(image, target_size=size)
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

    def normalize_icon_canvas(self, image: Image.Image, *, target_size: int = 256) -> Image.Image:
        icon = image.convert("RGBA")
        alpha_bbox = icon.getchannel("A").getbbox()
        if alpha_bbox is None:
            return Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))

        left, top, right, bottom = alpha_bbox
        content_width = right - left
        content_height = bottom - top
        content_center_x = left + content_width / 2
        content_center_y = top + content_height / 2
        canvas_center = target_size / 2
        is_small = content_width < target_size * 0.65 and content_height < target_size * 0.65
        is_off_center = (
            abs(content_center_x - canvas_center) > target_size * 0.15
            or abs(content_center_y - canvas_center) > target_size * 0.15
        )

        if not is_small and not is_off_center:
            return icon

        cropped = icon.crop(alpha_bbox)
        max_dimension = max(content_width, content_height)
        if max_dimension <= 0:
            return Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))

        normalized_max = max(1, round(target_size * 0.78))
        scale = normalized_max / max_dimension
        resized_size = (
            max(1, round(content_width * scale)),
            max(1, round(content_height * scale)),
        )
        resized_icon = cropped.resize(resized_size, Image.Resampling.LANCZOS)
        normalized = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
        paste_position = (
            (target_size - resized_size[0]) // 2,
            (target_size - resized_size[1]) // 2,
        )
        normalized.paste(resized_icon, paste_position, resized_icon)
        return normalized

    def _is_windows(self) -> bool:
        return os.name == "nt"

    def _extract_icon(self, source_path: Path):
        icon_handle = self._extract_shell_image_list_icon(source_path)
        if icon_handle:
            return icon_handle
        return self._extract_large_icon(source_path)

    def _extract_shell_image_list_icon(self, source_path: Path):
        shell32 = ctypes.windll.shell32
        shfileinfo = SHFILEINFOW()
        result = shell32.SHGetFileInfoW(
            str(source_path),
            0,
            ctypes.byref(shfileinfo),
            ctypes.sizeof(shfileinfo),
            SHGFI_SYSICONINDEX,
        )
        if result == 0 or shfileinfo.iIcon < 0:
            return None

        for image_list_size in (SHIL_JUMBO, SHIL_EXTRALARGE):
            icon_handle = self._get_system_image_list_icon(shfileinfo.iIcon, image_list_size)
            if icon_handle:
                return icon_handle
        return None

    def _get_system_image_list_icon(self, icon_index: int, image_list_size: int):
        shell32 = ctypes.windll.shell32
        image_list_pointer = ctypes.c_void_p()
        result = shell32.SHGetImageList(
            image_list_size,
            ctypes.byref(IID_IImageList),
            ctypes.byref(image_list_pointer),
        )
        if result != 0 or not image_list_pointer:
            return None

        image_list = ctypes.cast(image_list_pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
        icon_handle = ctypes.c_void_p()
        try:
            get_icon = ctypes.WINFUNCTYPE(
                ctypes.c_long,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_uint,
                ctypes.POINTER(ctypes.c_void_p),
            )(image_list.contents[IIMAGELIST_GETICON_INDEX])
            if get_icon(image_list_pointer, icon_index, ILD_TRANSPARENT, ctypes.byref(icon_handle)) != 0:
                return None
            return icon_handle.value
        finally:
            release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(image_list.contents[IUNKNOWN_RELEASE_INDEX])
            release(image_list_pointer)

    def _extract_large_icon(self, source_path: Path):
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
SHGFI_SYSICONINDEX = 0x000004000
SHIL_LARGE = 0x0
SHIL_EXTRALARGE = 0x2
SHIL_JUMBO = 0x4
ILD_TRANSPARENT = 0x00000001
IUNKNOWN_RELEASE_INDEX = 2
IIMAGELIST_GETICON_INDEX = 10
DI_NORMAL = 0x0003
BI_RGB = 0
DIB_RGB_COLORS = 0


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


IID_IImageList = GUID(
    0x46EB5926,
    0x582E,
    0x4017,
    (ctypes.c_ubyte * 8)(0x9F, 0xDF, 0xE8, 0x99, 0x8D, 0xAA, 0x09, 0x50),
)


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
