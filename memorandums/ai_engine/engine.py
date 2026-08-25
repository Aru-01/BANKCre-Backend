# memorandums/ai_engine/engine.py
# Main entry point called by the Celery task.
# Integrates banker-ai logic with Django's PropertyFile and PropertyFileChunk models.

import os
import logging
from django.conf import settings
from sentence_transformers import SentenceTransformer
from memorandums.ai_engine.vectordb import VectorStore
from memorandums.ai_engine.utils import extract_text_from_file, split_text
from memorandums.ai_engine.extractors  import extract_all_sections

logger = logging.getLogger(__name__)

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _get_store_paths(memorandum_id: int) -> tuple:
    """Temporary FAISS vector store files for this memorandum generation run."""
    base_dir = os.path.join(
        settings.MEDIA_ROOT, "memorandums", "vector_stores", str(memorandum_id)
    )
    os.makedirs(base_dir, exist_ok=True)
    return (
        os.path.join(base_dir, "vector.index"),
        os.path.join(base_dir, "metadata.pkl"),
    )


def _chunks_exist_for_file(file_id: int) -> bool:
    """Check if embeddings are already saved in DB for this PropertyFile."""
    from properties.models import PropertyFileChunk

    return PropertyFileChunk.objects.filter(file_id=file_id).exists()


def _save_chunks_for_file(file_id: int, chunks: list, embeddings: list):
    """Persist text chunks + embeddings to PropertyFileChunk DB table."""
    from properties.models import PropertyFile, PropertyFileChunk

    pf = PropertyFile.objects.get(pk=file_id)
    PropertyFileChunk.objects.bulk_create(
        [
            PropertyFileChunk(
                file=pf,
                chunk_text=chunk,
                embedding=embedding,
                chunk_index=idx,
            )
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]
    )


def _load_chunks_into_store(file_id: int, vector_store: VectorStore):
    """Load pre-saved chunks from DB directly into the vector store (fast path)."""
    from properties.models import PropertyFileChunk

    chunks = (
        PropertyFileChunk.objects.filter(file_id=file_id)
        .order_by("chunk_index")
        .values_list("chunk_text", "embedding")
    )
    texts = []
    vectors = []
    for chunk_text, embedding in chunks:
        texts.append(chunk_text)
        vectors.append(embedding)
    if vectors:
        vector_store.add(vectors, texts)


def generate(memorandum_id: int, property_data: dict, document_file_ids: list) -> dict:
    """
    Main entry point called by the Celery task.

    Steps:
      1. Build a fresh FAISS vector store.
      2. Add structured property details as text.
      3. For each document PropertyFile:
           - If chunks exist in DB → load from DB (fast, no re-embedding)
           - If no chunks yet → extract text, split, embed, save to DB
      4. Extract all 14 sections via Claude claude-sonnet-4-6.
      5. Cleanup temporary vector store files.

    Returns:
      dict keyed by section_key:
        {
          "property_information": {"type": "text", "content": "..."},
          "executive_summary":    {"type": "text", "content": "..."},
          "financing_summary":    {"type": "table", "content": {"columns": [...], "rows": [...]}},
          ...
        }
    """
    index_path, meta_path = _get_store_paths(memorandum_id)
    vector_store = VectorStore(dim=384, index_path=index_path, meta_path=meta_path)
    vector_store.clear()

    embedding_model = _get_embedding_model()

    # ── Step 1: Add structured property details ────────────────────────────
    prop_text = (
        f"Property: {property_data.get('property_name')}\n"
        f"Address: {property_data.get('property_address')}\n"
        f"Type: {property_data.get('property_type')}\n"
        f"Units: {property_data.get('number_of_units')}\n"
        f"Area: {property_data.get('rentable_area')} SF\n"
        f"Built: {property_data.get('year_built')}\n"
        f"Renovated: {property_data.get('year_renovated')}\n"
        f"Occupancy: {property_data.get('occupancy')}%\n"
        f"Parking: {property_data.get('parking_spaces')}"
    )
    prop_embedding = embedding_model.encode([prop_text])[0].tolist()
    vector_store.add([prop_embedding], [prop_text])

    # ── Step 2: Process each document ─────────────────────────────────────
    from properties.models import PropertyFile

    for file_id in document_file_ids:
        try:
            pf = PropertyFile.objects.get(pk=file_id)
            file_path = pf.file.path

            if _chunks_exist_for_file(file_id):
                # Fast path: reuse saved embeddings
                _load_chunks_into_store(file_id, vector_store)
                logger.info("Loaded cached chunks for PropertyFile %s", file_id)
            else:
                # Slow path: extract, embed, save
                if not os.path.isfile(file_path):
                    logger.warning("File not found on disk: %s", file_path)
                    continue

                raw_text = extract_text_from_file(file_path)
                if not raw_text.strip():
                    logger.warning("No text extracted from file %s", file_path)
                    continue

                chunks = split_text(raw_text)
                if not chunks:
                    continue

                embeddings = embedding_model.encode(chunks, batch_size=32)
                embeddings_list = [e.tolist() for e in embeddings]

                vector_store.add(embeddings_list, chunks)
                _save_chunks_for_file(file_id, chunks, embeddings_list)
                logger.info(
                    "Embedded and saved %d chunks for PropertyFile %s",
                    len(chunks),
                    file_id,
                )

        except PropertyFile.DoesNotExist:
            logger.warning("PropertyFile %s not found, skipping.", file_id)
        except Exception as exc:
            logger.error("Error processing file %s: %s", file_id, exc)

    # ── Step 3: Extract all 14 sections ───────────────────────────────────
    results = extract_all_sections(vector_store, property_data)

    # ── Step 4: Cleanup temp files ─────────────────────────────────────────
    vector_store.cleanup()

    return results
