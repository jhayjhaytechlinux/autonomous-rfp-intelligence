from pathlib import Path

import pymupdf

from app.ingestion.pdf_parser import extract_text_from_pdf


def load_document(file_path: str | Path) -> dict:
    """
    Load an RFP document and return structured document information.

    Args:
        file_path: Path to the document.

    Returns:
        A dictionary containing document metadata and extracted text.

    Raises:
        FileNotFoundError: If the document does not exist.
        ValueError: If the document is not a supported file type.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Unsupported document type: {path.suffix}. "
            "Currently only PDF documents are supported."
        )

    text = extract_text_from_pdf(path)

    document = pymupdf.open(path)

    try:
        page_count = len(document)
    finally:
        document.close()

    return {
        "filename": path.name,
        "file_type": "pdf",
        "page_count": page_count,
        "text": text,
        "character_count": len(text),
    }
