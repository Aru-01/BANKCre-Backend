import logging
import requests
import tempfile
from django.core.files.base import ContentFile
from typing import List, Tuple

logger = logging.getLogger(__name__)

def download_images_from_urls(urls: List[str]) -> List[Tuple[str, ContentFile]]:
    """
    Downloads images from a list of URLs and returns a list of tuples containing (filename, ContentFile).
    Silently ignores failed downloads.
    """
    downloaded_files = []

    # Flatten & sanitize any unparsed or nested URL strings
    cleaned_urls = []
    for raw in urls:
        if not raw:
            continue
        s = str(raw).strip().strip("[]'\"")
        for part in s.split(","):
            part = part.strip().strip("'\"")
            if part.startswith("http"):
                cleaned_urls.append(part)

    for idx, url in enumerate(cleaned_urls):
        try:
            # We use a standard User-Agent because some servers block python-requests
            response = requests.get(
                url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}
            )
            if response.status_code == 200:
                # Try to guess the extension from Content-Type
                content_type = response.headers.get("Content-Type", "")
                ext = "jpg"
                if "png" in content_type:
                    ext = "png"
                elif "jpeg" in content_type:
                    ext = "jpg"
                elif "webp" in content_type:
                    ext = "webp"

                filename = f"map_photo_{idx}.{ext}"
                content = ContentFile(response.content, name=filename)
                downloaded_files.append((filename, content))
            else:
                logger.warning(
                    f"Failed to download image from {url}: Status {response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Exception while downloading image from {url}: {e}")

    return downloaded_files
