from server.utils.logger import get_logger

logger = get_logger(__name__)


def chunk_token(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Token-based chunking using LangChain's TokenTextSplitter (cl100k_base encoding).

    chunk_size and overlap are measured in tokens, not characters.
    cl100k_base is the tiktoken encoding used by GPT-3.5/GPT-4 (≈4 chars/token on average).
    """
    from langchain_text_splitters import TokenTextSplitter

    splitter = TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        encoding_name="cl100k_base",
    )
    return splitter.split_text(text)
