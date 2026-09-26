from pathlib import Path

import pymupdf


def extract_text_from_pdf(file_path: str | Path) -> str:
    """
    Extract all text from a PDF document.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Extracted text as a single string.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        ValueError: If the supplied file is not a PDF.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {path.suffix}")

    document = pymupdf.open(path)

    try:
        pages = []

        for page in document:
            text = page.get_text()

            if text.strip():
                pages.append(text.strip())

        return "\n\n".join(pages)

    finally:
        document.close()
