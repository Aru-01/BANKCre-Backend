# memorandums/ai_engine/utils.py
# Adapted from banker-ai/utils.py
# Text extraction from PDF, DOCX, and Images + tiktoken-based chunking.

import io
import os
import base64
import fitz          # PyMuPDF
import tiktoken
from docx import Document
from typing import List


def extract_text_from_pdf(file_path: str) -> str:
    """Extract full text from a PDF file on disk."""
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file on disk."""
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])


def extract_text_from_image(file_path: str) -> str:
    """
    Extract text from an image file using Claude Vision (claude-sonnet-4-6).
    Used when a document is an image (PNG, JPG, JPEG) — e.g. scanned financials.
    """
    import anthropic
    from django.conf import settings

    api_key = getattr(settings, "CLAUDE_API_KEY", None) or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("CLAUDE_API_KEY is not configured.")

    client = anthropic.Anthropic(api_key=api_key)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    ext = os.path.splitext(file_path)[1].lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")
    base64_image = base64.b64encode(file_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract all readable text from this image carefully and focus on accuracy.",
                    },
                ],
            }
        ],
    )
    return response.content[0].text.strip()


def extract_text_from_file(file_path: str) -> str:
    """
    Detect file type and extract text accordingly.
    Supports: PDF, DOCX, DOC, TXT, PNG, JPG, JPEG.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return extract_text_from_image(file_path)
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        # Fallback: try PDF parser
        try:
            return extract_text_from_pdf(file_path)
        except Exception:
            return ""


def split_text(text: str, max_tokens: int = 500) -> List[str]:
    """
    Split text into chunks using tiktoken token counting.
    More accurate than simple word-count splitting.
    """
    enc = tiktoken.get_encoding("cl100k_base")
    words = text.split()
    chunks, chunk = [], []
    tokens = 0

    for word in words:
        word_tokens = len(enc.encode(word))
        if tokens + word_tokens > max_tokens:
            if chunk:
                chunks.append(" ".join(chunk))
            chunk = [word]
            tokens = word_tokens
        else:
            chunk.append(word)
            tokens += word_tokens

    if chunk:
        chunks.append(" ".join(chunk))

    return chunks
