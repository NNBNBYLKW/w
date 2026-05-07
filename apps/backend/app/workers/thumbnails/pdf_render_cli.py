import argparse
from pathlib import Path
import traceback

from app.workers.thumbnails.pdf_generator import PdfThumbnailGeneratorWorker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the first PDF page to a thumbnail PNG.")
    parser.add_argument("--source", required=True, help="Source PDF path.")
    parser.add_argument("--output", required=True, help="Output PNG path.")
    parser.add_argument("--width", default=384, type=int, help="Target thumbnail width.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_path = Path(args.output)

    try:
        PdfThumbnailGeneratorWorker().generate_thumbnail(Path(args.source), output_path, width=args.width)
        if not output_path.exists() or output_path.stat().st_size <= 0:
            raise RuntimeError(f"PDF render CLI did not create a valid output file: {output_path}")
    except Exception:
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
