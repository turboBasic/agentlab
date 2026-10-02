from io import BytesIO
from pathlib import Path

from markitdown import MarkItDown, StreamInfo
from pydantic import Field


def binary_document_to_markdown(binary_data: bytes, file_type: str) -> str:
    """Converts binary document data to markdown-formatted text."""
    md = MarkItDown()
    file_obj = BytesIO(binary_data)
    stream_info = StreamInfo(extension=file_type)
    result = md.convert(file_obj, stream_info=stream_info)
    return result.text_content


def document_path_to_markdown(
    file_path: str = Field(description="Path to a .docx or .pdf file on disk"),
) -> str:
    """Convert a document on disk to markdown.

    Reads the file at the given path, infers the format from its extension
    and returns the content as markdown-formatted text.

    When to use:
    - When you have a local .docx or .pdf file and need its text content
    - Not for in-memory data; use binary_document_to_markdown for that

    Examples:
    >>> document_path_to_markdown("report.pdf")
    '# Report\\n...'
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    return binary_document_to_markdown(path.read_bytes(), path.suffix)
