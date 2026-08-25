import logging
from celery import shared_task
from django.apps import apps

from memorandums.ai_engine.extractors import (
    SECTION_ORDER,
    TEXT_SECTIONS,
    TABLE_SECTIONS,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1)
def generate_memorandum_task(self, memorandum_id: int):
    """
    Background Celery task that:
      1. Fetches the Memorandum and its related Property + document files.
      2. Calls engine.generate() from ai_engine/.
      3. Creates 14 MemorandumSection records (text + table types).
      4. Sets status to 'Draft' on success or 'Failed' on error.
    """
    Memorandum = apps.get_model("memorandums", "Memorandum")
    MemorandumSection = apps.get_model("memorandums", "MemorandumSection")

    try:
        memorandum = Memorandum.objects.select_related("property").get(pk=memorandum_id)
    except Memorandum.DoesNotExist:
        logger.error("Memorandum %s not found.", memorandum_id)
        return

    try:
        prop = memorandum.property

        # Build property data dict for the engine
        property_data = {
            "property_name": prop.property_name,
            "property_address": prop.property_address,
            "property_type": prop.property_type,
            "number_of_units": prop.number_of_units,
            "rentable_area": str(prop.rentable_area),
            "year_built": prop.year_built,
            "year_renovated": prop.year_renovated,
            "occupancy": str(prop.occupancy),
            "parking_spaces": prop.parking_spaces,
            "latitude": str(prop.latitude),
            "longitude": str(prop.longitude),
        }

        # Collect IDs of all uploaded documents for this property
        from properties.models import PropertyFile

        document_file_ids = list(
            PropertyFile.objects.filter(
                property=prop,
                category=PropertyFile.CATEGORY_DOCUMENT,
            ).values_list("id", flat=True)
        )

        logger.info(
            "Generating memorandum %s for property '%s' with %d document(s).",
            memorandum_id,
            prop.property_name,
            len(document_file_ids),
        )

        # Run the AI engine
        from memorandums.ai_engine import engine

        sections_data = engine.generate(memorandum_id, property_data, document_file_ids)

        # Create MemorandumSection records
        sections_to_create = []
        for order, section_key in enumerate(SECTION_ORDER):
            section_result = sections_data.get(section_key, {})
            section_type = section_result.get("type", "text")
            raw_content = section_result.get("content", "")

            if section_type == "table":
                section = MemorandumSection(
                    memorandum=memorandum,
                    section_key=section_key,
                    section_type=MemorandumSection.SECTION_TYPE_TABLE,
                    content="",
                    table_data=raw_content if isinstance(raw_content, dict) else {},
                    order=order,
                )
            else:
                section = MemorandumSection(
                    memorandum=memorandum,
                    section_key=section_key,
                    section_type=MemorandumSection.SECTION_TYPE_TEXT,
                    content=raw_content if isinstance(raw_content, str) else "",
                    table_data=None,
                    order=order,
                )
            sections_to_create.append(section)

        MemorandumSection.objects.bulk_create(sections_to_create)

        # Mark as Draft
        memorandum.status = Memorandum.STATUS_DRAFT
        memorandum.save(update_fields=["status", "updated_at"])

        logger.info("Memorandum %s generated successfully.", memorandum_id)

    except Exception as exc:
        logger.error(
            "Memorandum %s generation failed: %s", memorandum_id, exc, exc_info=True
        )
        Memorandum.objects.filter(pk=memorandum_id).update(
            status=Memorandum.STATUS_FAILED
        )
        raise self.retry(exc=exc, countdown=0)


@shared_task
def regenerate_section_task(
    memorandum_id: int, section_id: int, custom_instruction: str = ""
):
    """
    Regenerate a single TEXT section for a memorandum using Claude.
    Table sections are NOT regenerable (data accuracy requirement).
    """
    Memorandum = apps.get_model("memorandums", "Memorandum")
    MemorandumSection = apps.get_model("memorandums", "MemorandumSection")

    try:
        memorandum = Memorandum.objects.select_related("property").get(pk=memorandum_id)
        section = MemorandumSection.objects.get(pk=section_id, memorandum=memorandum)
    except (Memorandum.DoesNotExist, MemorandumSection.DoesNotExist) as e:
        logger.error("Regenerate failed: %s", e)
        return

    if section.section_type == MemorandumSection.SECTION_TYPE_TABLE:
        logger.warning(
            "Section %s is a table section — regeneration not allowed.",
            section.section_key,
        )
        return

    prop = memorandum.property
    property_data = {
        "property_name": prop.property_name,
        "property_address": prop.property_address,
        "property_type": prop.property_type,
        "number_of_units": prop.number_of_units,
        "rentable_area": str(prop.rentable_area),
        "year_built": prop.year_built,
        "year_renovated": prop.year_renovated,
        "occupancy": str(prop.occupancy),
        "parking_spaces": prop.parking_spaces,
    }

    from properties.models import PropertyFile
    from memorandums.ai_engine.vectordb import VectorStore
    from memorandums.ai_engine import engine
    from memorandums.ai_engine.extractors import extract_text_section

    # Collect document file IDs
    document_file_ids = list(
        PropertyFile.objects.filter(
            property=prop, category=PropertyFile.CATEGORY_DOCUMENT
        ).values_list("id", flat=True)
    )

    # Rebuild vector store (reuses cached chunks from DB via engine.generate internals)
    index_path, meta_path = engine._get_store_paths(memorandum_id)
    vector_store = VectorStore(dim=384, index_path=index_path, meta_path=meta_path)
    vector_store.clear()

    # Re-add property details
    from sentence_transformers import SentenceTransformer

    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    prop_text = (
        f"Property: {property_data['property_name']}\n"
        f"Address: {property_data['property_address']}"
    )
    vector_store.add([embedding_model.encode([prop_text])[0].tolist()], [prop_text])

    # Load document chunks (fast path from DB)
    for file_id in document_file_ids:
        try:
            if engine._chunks_exist_for_file(file_id):
                engine._load_chunks_into_store(file_id, vector_store)
            else:
                pf = PropertyFile.objects.get(pk=file_id)
                from memorandums.ai_engine.utils import (
                    extract_text_from_file,
                    split_text,
                )

                raw_text = extract_text_from_file(pf.file.path)
                chunks = split_text(raw_text)
                if chunks:
                    embeddings = embedding_model.encode(chunks, batch_size=32)
                    embeddings_list = [e.tolist() for e in embeddings]
                    vector_store.add(embeddings_list, chunks)
                    engine._save_chunks_for_file(file_id, chunks, embeddings_list)
        except Exception as exc:
            logger.error("Error loading file %s for regeneration: %s", file_id, exc)

    # Regenerate just this one section
    new_content = extract_text_section(
        vector_store,
        section.section_key,
        custom_instruction,
        property_data=property_data,
    )
    section.content = new_content
    section.save(update_fields=["content", "updated_at"])

    vector_store.cleanup()
    logger.info(
        "Section '%s' regenerated for memorandum %s.",
        section.section_key,
        memorandum_id,
    )
