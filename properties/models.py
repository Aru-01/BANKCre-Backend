import os
from django.db import models
from django.conf import settings


# Upload path helpers
def property_file_upload_path(instance, filename):
    """
    Organises all property files (images + documents) under:
      media/properties/<property_id>/files/<filename>
    """
    return f"properties/{instance.property.id}/files/{filename}"


# Property
class Property(models.Model):
    # Location
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    # Property details
    property_name = models.CharField(max_length=255)
    property_address = models.TextField()
    property_type = models.CharField(max_length=100)
    number_of_units = models.IntegerField()
    rentable_area = models.DecimalField(max_digits=12, decimal_places=2)
    year_built = models.IntegerField()
    year_renovated = models.IntegerField(null=True, blank=True)
    occupancy = models.DecimalField(max_digits=5, decimal_places=2)
    parking_spaces = models.IntegerField()

    # Ownership
    sponsor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    sponsor_role = models.ForeignKey(
        "accounts.RoleModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="properties",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.property_name

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sponsor"]),
        ]


# Property Files  (images + documents, unified)
class PropertyFile(models.Model):
    """
    Single model for ALL files attached to a property.

    category  — 'image'    : property photo (from map fetch or manual upload)
              — 'document' : PDF, DOCX, XLSX, etc.

    image_source (only relevant when category='image'):
              — 'map'    : fetched from Google Maps by the frontend
              — 'manual' : uploaded directly by the sponsor
    """

    CATEGORY_IMAGE = "image"
    CATEGORY_DOCUMENT = "document"
    CATEGORY_CHOICES = [
        (CATEGORY_IMAGE, "Image"),
        (CATEGORY_DOCUMENT, "Document"),
    ]

    SOURCE_MAP = "map"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [
        (SOURCE_MAP, "From Map"),
        (SOURCE_MANUAL, "Manual Upload"),
    ]

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="files",
    )
    file = models.FileField(upload_to=property_file_upload_path)

    # What kind of file this is
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20)
    image_source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
        blank=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_property_files",
    )
    uploaded_by_role = models.ForeignKey(
        "accounts.RoleModel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="property_files",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.property.property_name} — [{self.category}] {self.file_name}"

    def delete(self, *args, **kwargs):
        """Remove the physical file from storage when the record is deleted."""
        if self.file:
            try:
                if os.path.isfile(self.file.path):
                    os.remove(self.file.path)
            except (ValueError, OSError):
                pass
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Property File"
        verbose_name_plural = "Property Files"
        ordering = ["category", "uploaded_at"]
        indexes = [
            models.Index(fields=["property", "category"]),
            models.Index(fields=["uploaded_by"]),
        ]


# RAG chunks (text extracted + embedded from documents)
class PropertyFileChunk(models.Model):
    """
    Stores extracted text chunks and their embeddings for a PropertyFile
    whose category='document'.
    All chunks for a property are automatically loaded as AI context
    when the user starts a chat.
    """

    file = models.ForeignKey(
        PropertyFile,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_text = models.TextField()
    embedding = models.JSONField()
    chunk_index = models.PositiveIntegerField()

    class Meta:
        verbose_name = "File Chunk"
        verbose_name_plural = "File Chunks"
        ordering = ["file", "chunk_index"]
        indexes = [
            models.Index(fields=["file", "chunk_index"]),
        ]

    def __str__(self):
        return f"{self.file} — chunk {self.chunk_index}"


# Chat Session & Messages
class PropertyChatSession(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_chat_sessions",
    )
    title = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Property Chat Session"
        verbose_name_plural = "Property Chat Sessions"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["property", "user"]),
        ]

    def __str__(self):
        return f'{self.property.property_name} — {self.user.email} — {self.title or "Untitled"}'


class PropertyChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    session = models.ForeignKey(
        PropertyChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Property Chat Message"
        verbose_name_plural = "Property Chat Messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
