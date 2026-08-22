"""
Property AI Chatbot Engine — OpenAI gpt-4o-mini
RAG strategy: FAISS + sentence-transformers (all-MiniLM-L6-v2)

All document chunks for the selected property are automatically indexed.
The user selects a property → every uploaded document is in context.
"""

import os
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded to avoid slowing down Django startup
_embed_model = None

SYSTEM_PROMPT = (
    "You are a knowledgeable real estate assistant. "
    "Answer questions strictly based on the context extracted from the "
    "property's documents. If the answer is not found in the context, "
    "say so clearly. Be concise, factual, and professional."
)

CHUNK_SIZE    = 600   # chars per chunk
CHUNK_OVERLAP = 80    # overlap between consecutive chunks


# ──────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────

def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _embed_model


def _get_openai_client():
    from django.conf import settings
    from openai import OpenAI
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        raise ValueError('OPENAI_API_KEY is not configured.')
    return OpenAI(api_key=api_key)


# ──────────────────────────────────────────────────
# Retrieval (FAISS over ALL property docs)
# ──────────────────────────────────────────────────

def _retrieve(property_id: int, query: str, top_k: int = 8) -> list[str]:
    """
    Semantically retrieve the top-k most relevant text chunks for `query`
    from ALL document files belonging to `property_id`.
    """
    import faiss
    from properties.models import PropertyFileChunk

    rows = list(
        PropertyFileChunk.objects
        .filter(file__property_id=property_id, file__category='document')
        .select_related('file')
        .order_by('file_id', 'chunk_index')
    )

    if not rows:
        return []

    chunks     = [r.chunk_text for r in rows]
    embeddings = np.array([r.embedding for r in rows], dtype='float32')

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    model     = _get_embed_model()
    query_vec = model.encode([query])[0].astype('float32').reshape(1, -1)
    _, idxs   = index.search(query_vec, min(top_k, index.ntotal))

    return [chunks[i] for i in idxs[0] if 0 <= i < len(chunks)]


# ──────────────────────────────────────────────────
# Public API — ask()
# ──────────────────────────────────────────────────

def ask(property_id: int, message: str, history: list[dict] | None = None) -> str:
    """
    Answer `message` using all documents of `property_id` as context.
    `history` — list of {'role': ..., 'content': ...} dicts, oldest first.
    Uses OpenAI gpt-4o-mini.
    """
    context = _retrieve(property_id, message)
    if not context:
        return (
            'No document data is available for this property yet. '
            'Please upload some documents first.'
        )

    context_text = '\n\n'.join(context)
    history      = history or []

    client   = _get_openai_client()
    messages = [
        {'role': 'system', 'content': f'{SYSTEM_PROMPT}\n\nContext:\n{context_text}'}
    ]
    for msg in history:
        messages.append({'role': msg['role'], 'content': msg['content']})
    messages.append({'role': 'user', 'content': message})

    try:
        response = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error('OpenAI chat failed: %s', exc)
        raise RuntimeError('AI service is currently unavailable.') from exc


# ──────────────────────────────────────────────────
# Public API — ingest_file()
# ──────────────────────────────────────────────────

def _extract_text(file_path: str, ext: str) -> str:
    """Extract plain text from a file. Returns empty string on failure."""
    ext = ext.lower().lstrip('.')

    if ext == 'pdf':
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return '\n'.join(page.extract_text() or '' for page in pdf.pages)
        except Exception as exc:
            logger.warning('pdfplumber failed for %s: %s', file_path, exc)
            return ''

    if ext in ('docx', 'doc'):
        try:
            import docx
            return '\n'.join(p.text for p in docx.Document(file_path).paragraphs)
        except Exception as exc:
            logger.warning('python-docx failed for %s: %s', file_path, exc)
            return ''

    if ext in ('txt', 'csv'):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as exc:
            logger.warning('Text read failed for %s: %s', file_path, exc)
            return ''

    if ext in ('xlsx', 'xls'):
        try:
            import openpyxl
            wb   = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            rows = []
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    rows.append('\t'.join('' if c is None else str(c) for c in row))
            return '\n'.join(rows)
        except Exception as exc:
            logger.warning('openpyxl failed for %s: %s', file_path, exc)
            return ''

    # PNG/JPG/etc — no OCR; skip
    return ''


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping fixed-size chunks."""
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + CHUNK_SIZE].strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if c]


def ingest_file(file_id: int) -> int:
    """
    Extract text from a PropertyFile (category='document'), chunk + embed it,
    and persist chunks to PropertyFileChunk.

    Existing chunks are deleted first (idempotent re-ingestion).
    Returns number of chunks saved (0 = unsupported type or empty file).
    """
    from properties.models import PropertyFile, PropertyFileChunk

    pfile = PropertyFile.objects.select_related('property').get(pk=file_id)

    if pfile.category != PropertyFile.CATEGORY_DOCUMENT:
        return 0

    # Remove stale chunks before re-indexing
    PropertyFileChunk.objects.filter(file=pfile).delete()

    try:
        file_path = pfile.file.path
    except (ValueError, NotImplementedError):
        logger.warning('ingest_file: cannot resolve path for file %s', file_id)
        return 0

    text = _extract_text(file_path, pfile.file_type)
    if not text.strip():
        return 0

    chunks = _chunk_text(text)
    if not chunks:
        return 0

    model      = _get_embed_model()
    embeddings = model.encode(chunks, batch_size=32, show_progress_bar=False)

    PropertyFileChunk.objects.bulk_create([
        PropertyFileChunk(
            file        = pfile,
            chunk_text  = chunk,
            embedding   = emb.tolist(),
            chunk_index = idx,
        )
        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ])

    logger.info('ingest_file: file %s (%s) → %d chunks.', file_id, pfile.file_name, len(chunks))
    return len(chunks)
