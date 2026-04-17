from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


class ThumbnailGeneratorWorker:
    def generate_thumbnail(self, source_path: Path, output_path: Path, *, longest_edge: int = 640) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(source_path) as image:
            normalized = ImageOps.exif_transpose(image)
            prepared = self._prepare_for_jpeg(normalized)
            prepared.thumbnail((longest_edge, longest_edge))
            prepared.save(output_path, format="JPEG", quality=85, optimize=True)

    def is_expected_generation_failure(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
                UnidentifiedImageError,
            ),
        )

    def _prepare_for_jpeg(self, image: Image.Image) -> Image.Image:
        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, (13, 17, 23))
            alpha_channel = image.getchannel("A")
            background.paste(image.convert("RGB"), mask=alpha_channel)
            return background

        if image.mode == "P" and "transparency" in image.info:
            rgba_image = image.convert("RGBA")
            background = Image.new("RGB", rgba_image.size, (13, 17, 23))
            background.paste(rgba_image.convert("RGB"), mask=rgba_image.getchannel("A"))
            return background

        return image.convert("RGB")
