import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class PdfThumbnailGenerationError(RuntimeError):
    pass


class PdfThumbnailGeneratorWorker:
    def generate_thumbnail(self, source_path: Path, output_path: Path, *, width: int = 384) -> None:
        logger.info("PDF thumbnail generator called source_path=%s output_path=%s width=%s", source_path, output_path, width)
        if not source_path.exists():
            logger.info("PDF thumbnail source file does not exist source_path=%s", source_path)
            raise PdfThumbnailGenerationError("PDF file does not exist.")

        temporary_path = output_path.with_name(f".{output_path.stem}.tmp.png")
        if temporary_path.exists():
            temporary_path.unlink()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            image = self._render_first_page(source_path, width=width)
            image.save(temporary_path, format="PNG")
            temporary_path.replace(output_path)
        except Exception as error:
            if temporary_path.exists():
                temporary_path.unlink()
            if self.is_expected_generation_failure(error):
                logger.info("PDF thumbnail generation failed source_path=%s output_path=%s reason=%s", source_path, output_path, error)
                raise PdfThumbnailGenerationError("PDF thumbnail could not be generated.") from error
            raise

        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.info("PDF thumbnail output file was not created output_path=%s", output_path)
            raise PdfThumbnailGenerationError("PDF thumbnail output file was not created.")
        logger.info("PDF thumbnail output created output_path=%s bytes=%s", output_path, output_path.stat().st_size)

    def is_expected_generation_failure(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                ImportError,
                FileNotFoundError,
                NotADirectoryError,
                PermissionError,
                OSError,
                ValueError,
                PdfThumbnailGenerationError,
            ),
        )

    def _render_first_page(self, source_path: Path, *, width: int) -> Image.Image:
        try:
            import pypdfium2 as pdfium
        except ImportError as error:
            logger.info("pypdfium2 import failed while rendering PDF thumbnail source_path=%s reason=%s", source_path, error)
            raise PdfThumbnailGenerationError("pypdfium2 is not available.") from error

        pdf = None
        page = None
        bitmap = None
        try:
            pdf = pdfium.PdfDocument(str(source_path))
            if len(pdf) < 1:
                logger.info("PDF has no pages source_path=%s", source_path)
                raise PdfThumbnailGenerationError("PDF has no pages.")

            page = pdf[0]
            page_width, _ = page.get_size()
            if page_width <= 0:
                logger.info("PDF page has invalid dimensions source_path=%s page_width=%s", source_path, page_width)
                raise PdfThumbnailGenerationError("PDF page has invalid dimensions.")

            scale = width / page_width
            bitmap = page.render(scale=scale)
            rendered = bitmap.to_pil().convert("RGBA")
            background = Image.new("RGBA", rendered.size, (255, 255, 255, 255))
            background.alpha_composite(rendered)
            return background
        except PdfThumbnailGenerationError:
            raise
        except Exception as error:
            logger.info("PDF first-page render failed source_path=%s reason=%s", source_path, error)
            raise PdfThumbnailGenerationError("PDF first page could not be rendered.") from error
        finally:
            if bitmap is not None and hasattr(bitmap, "close"):
                bitmap.close()
            if page is not None and hasattr(page, "close"):
                page.close()
            if pdf is not None and hasattr(pdf, "close"):
                pdf.close()

    def render_pages(self, file_path: str, max_pages: int = 5) -> list[Image.Image]:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(file_path)
        pages = []
        for i in range(min(len(doc), max_pages)):
            page = doc[i]
            bitmap = page.render(scale=1.5)
            pil_image = Image.frombytes("RGBA", (bitmap.width, bitmap.height), bitmap.data)
            pages.append(pil_image)
        return pages
