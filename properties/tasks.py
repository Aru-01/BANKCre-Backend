# properties/tasks.py
import os
import logging
from celery import shared_task
from django.contrib.auth import get_user_model

from properties.chatbot import ingest_file
from properties.services.file_services import download_images_from_urls
from properties.models import Property, PropertyFile
from accounts.models import RoleModel

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def my_background_task(data):
    import time
    time.sleep(10)
    print(f"Task completed with data: {data}")
    return "Done!"

@shared_task
def ingest_file_task(file_id):
    try:
        ingest_file(file_id)
        logger.info(f"Successfully ingested file {file_id}")
    except Exception as exc:
        logger.error(f"ingest_file failed for file {file_id}: {exc}")

@shared_task
def download_map_images_task(photo_urls, property_id, user_id, role_id):
    try:
        prop = Property.objects.get(id=property_id)
        user = User.objects.get(id=user_id)
        role = RoleModel.objects.get(id=role_id)
        
        downloaded = download_images_from_urls(photo_urls)
        for filename, content in downloaded:
            ext = os.path.splitext(filename)[1].lstrip(".").lower()
            PropertyFile.objects.create(
                property=prop,
                file=content,
                category=PropertyFile.CATEGORY_IMAGE,
                file_name=filename,
                file_type=ext,
                image_source=PropertyFile.SOURCE_MAP,
                uploaded_by=user,
                uploaded_by_role=role,
            )
        logger.info(f"Successfully downloaded {len(downloaded)} map images for property {property_id}")
    except Exception as exc:
        logger.error(f"Failed to download map images for property {property_id}: {exc}")
