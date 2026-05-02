from pypdf import PdfReader
from server.utils.logger import get_logger

logger = get_logger(__name__)


def parse_pdf(pdf_path: str) -> str:
    """Extract text from PDF file using pypdf."""
    logger.info(f"Parsing PDF: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)
        text_parts = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
                logger.debug(f"Extracted {len(page_text)} chars from page {i + 1}")

        full_text = "\n\n".join(text_parts)
        logger.info(f"Parsed {len(reader.pages)} pages, {len(full_text)} total chars")

        return full_text

    except Exception as e:
        logger.error(f"Failed to parse PDF {pdf_path}: {e}")
        raise
