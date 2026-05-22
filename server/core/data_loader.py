from pathlib import Path

from pypdf import PdfReader

from server.utils.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv"}


def resolve_data_paths(data_paths: list[str]) -> list[Path]:
    """Expand a mix of file paths and directories into individual file paths.

    Directories are scanned recursively for supported file types.
    Raises FileNotFoundError if any explicit path doesn't exist.
    """
    resolved: list[Path] = []

    for raw in data_paths:
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(f"Data path not found: {raw}")

        if path.is_dir():
            found = sorted(
                f
                for f in path.rglob("*")
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            if not found:
                logger.warning(f"No supported files in directory: {raw}")
            resolved.extend(found)
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            resolved.append(path)
        else:
            logger.warning(f"Skipping unsupported file type: {raw}")

    logger.info(f"Resolved {len(resolved)} file(s) from {len(data_paths)} path(s)")
    return resolved


def load_file(path: Path) -> str:
    """Parse a single file into text based on its extension."""
    ext = path.suffix.lower()
    logger.info(f"Loading {ext} file: {path}")

    if ext == ".pdf":
        return _parse_pdf(path)
    return path.read_text(encoding="utf-8")


def load_all_files(data_paths: list[str]) -> str:
    """Resolve paths, parse all files, and return concatenated text."""
    file_paths = resolve_data_paths(data_paths)
    if not file_paths:
        raise ValueError("No supported files found in the provided data_paths")

    texts: list[str] = []
    for fp in file_paths:
        texts.append(load_file(fp))

    combined = "\n\n".join(texts)
    logger.info(f"Loaded {len(file_paths)} file(s), {len(combined)} total chars")
    return combined


def _parse_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file using pypdf."""
    reader = PdfReader(str(pdf_path))
    text_parts = []

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)
            logger.debug(f"Extracted {len(page_text)} chars from page {i + 1}")

    full_text = "\n\n".join(text_parts)
    if not full_text.strip():
        logger.warning(f"PDF {pdf_path}: extracted 0 chars from {len(reader.pages)} page(s)")
    else:
        logger.info(f"Parsed {len(reader.pages)} pages, {len(full_text)} total chars")
    return full_text
