import json
from pathlib import Path
import fitz  # PyMuPDF


STRUCTURE_FILE = Path("structure.json")
OUTPUT_PDF = Path("All_In_One.pdf")
OUTPUT_PDF_WITH_TOC = Path("All_In_One_With_Bookmarks.pdf")


def load_structure(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def walk_nodes(cfg: dict):
    """
    Yields tuples: (level, title, file)
    level: 1=Home, 2=Section, 3=Subsection, etc. (bookmarks levels)
    """
    home = cfg.get("home")
    if not home:
        raise ValueError("structure.json must contain a 'home' object.")

    yield (1, home.get("title", "Home"), home.get("file"))

    def walk_children(nodes, level):
        for node in nodes:
            yield (level, node.get("title", "Untitled"), node.get("file"))
            children = node.get("children", [])
            if children:
                yield from walk_children(children, level + 1)

    yield from walk_children(cfg.get("sections", []), level=2)


def merge_pdfs(ordered_files: list[Path]) -> fitz.Document:
    out = fitz.open()
    for f in ordered_files:
        if not f.exists():
            raise FileNotFoundError(f"Missing PDF: {f}")
        src = fitz.open(f)
        if src.page_count != 1:
            raise ValueError(f"{f} must be 1 page, but has {src.page_count} pages.")
        out.insert_pdf(src)
        src.close()
    return out


def main():
    cfg = load_structure(STRUCTURE_FILE)

    nodes = list(walk_nodes(cfg))  # [(level,title,file), ...]
    files = []
    for level, title, file in nodes:
        if not file:
            raise ValueError(f"Node '{title}' is missing a 'file' value in structure.json.")
        files.append(Path(file))

    # Merge
    doc = merge_pdfs(files)
    doc.save(OUTPUT_PDF)
    doc.close()
    print(f"Created merged PDF: {OUTPUT_PDF}")

    # Merge again + add bookmarks (TOC)
    doc = merge_pdfs(files)
    toc = []
    for i, (level, title, _file) in enumerate(nodes):
        # PyMuPDF TOC pages are 1-based
        toc.append([level, title, i + 1])
    doc.set_toc(toc)
    doc.save(OUTPUT_PDF_WITH_TOC)
    doc.close()
    print(f"Created merged PDF with bookmarks: {OUTPUT_PDF_WITH_TOC}")


if __name__ == "__main__":
    main()
