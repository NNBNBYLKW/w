import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text.append(data.strip())


class EpubParser:
    def parse(self, file_path: str) -> dict:
        with zipfile.ZipFile(file_path) as zf:
            container = ET.parse(zf.open("META-INF/container.xml"))
            nsmap = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
            rootfile = container.find(".//c:rootfile", nsmap)
            if rootfile is None:
                return {"title": None, "author": None, "chapters": []}
            opf_path = rootfile.get("full-path", "")
            opf_dir = str(Path(opf_path).parent)
            opf = ET.parse(zf.open(opf_path))
            dc_ns = {"dc": "http://purl.org/dc/elements/1.1/"}
            title_el = opf.find(".//dc:title", dc_ns)
            author_el = opf.find(".//dc:creator", dc_ns)
            title = title_el.text if title_el is not None else None
            author = author_el.text if author_el is not None else None

            opf_ns = "http://www.idpf.org/2007/opf"
            spine = opf.findall(f".//{{{opf_ns}}}itemref")
            manifest = {item.get("id"): item.get("href") for item in opf.findall(f".//{{{opf_ns}}}item")}

            chapters = []
            for itemref in spine:
                idref = itemref.get("id")
                href = manifest.get(idref)
                if href is None:
                    continue
                chapter_path = str(Path(opf_dir) / href) if opf_dir != "." else href
                try:
                    content = zf.read(chapter_path).decode("utf-8", errors="replace")
                    extractor = TextExtractor()
                    extractor.feed(content)
                    text = " ".join(extractor.text).strip()
                    if text:
                        chapters.append({"title": href, "text": text[:5000]})  # limit per chapter
                except Exception:
                    pass
            return {"title": title, "author": author, "chapters": chapters}
