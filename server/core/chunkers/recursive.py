from langchain_text_splitters import RecursiveCharacterTextSplitter

from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_recursive(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Chunk text using LangChain's RecursiveCharacterTextSplitter."""

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = splitter.split_text(text)
    logger.info(f"Recursive chunking produced {len(chunks)} chunks")

    return chunks
