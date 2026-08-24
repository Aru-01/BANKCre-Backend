import os

# File constraints
MAX_DOC_SIZE_MB = 25
MAX_DOC_SIZE_BYTES = MAX_DOC_SIZE_MB * 1024 * 1024

MAX_IMG_SIZE_MB = 10
MAX_IMG_SIZE_BYTES = MAX_IMG_SIZE_MB * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

ALLOWED_DOCUMENT_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "xlsx",
    "xls",
    "csv",
    "pptx",
    "ppt",
    "docx",
    "doc",
    "txt",
}


# Single-file validators
def validate_image_file(file):
    """
    Validate a single image file for size and extension.
    Returns (True, None) on success or (False, error_message) on failure.
    """
    if file.size > MAX_IMG_SIZE_BYTES:
        size_mb = file.size / (1024 * 1024)
        return False, (
            f"'{file.name}' exceeds the maximum allowed size of {MAX_IMG_SIZE_MB} MB "
            f"(uploaded: {size_mb:.2f} MB)."
        )
    ext = os.path.splitext(file.name)[1].lstrip(".").lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, (
            f"'{file.name}' has an unsupported image type (.{ext}). "
            f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )
    return True, None


def validate_document_file(file):
    """
    Validate a single document file for size and extension.
    Returns (True, None) on success or (False, error_message) on failure.
    """
    if file.size > MAX_DOC_SIZE_BYTES:
        size_mb = file.size / (1024 * 1024)
        return False, (
            f"'{file.name}' exceeds the maximum allowed size of {MAX_DOC_SIZE_MB} MB "
            f"(uploaded: {size_mb:.2f} MB)."
        )
    ext = os.path.splitext(file.name)[1].lstrip(".").lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        return False, (
            f"'{file.name}' has an unsupported file type (.{ext}). "
            f"Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}."
        )
    return True, None


# Batch validators
def validate_images(files):
    """Validate a list of image files. Returns (valid_files, errors)."""
    valid_files, errors = [], []
    for file in files:
        ok, msg = validate_image_file(file)
        if ok:
            valid_files.append(file)
        else:
            errors.append(msg)
    return valid_files, errors


def validate_documents(files):
    """Validate a list of document files. Returns (valid_files, errors)."""
    valid_files, errors = [], []
    for file in files:
        ok, msg = validate_document_file(file)
        if ok:
            valid_files.append(file)
        else:
            errors.append(msg)
    return valid_files, errors
