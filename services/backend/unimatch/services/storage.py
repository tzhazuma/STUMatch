"""Storage providers: local filesystem + MinIO."""
import logging
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from unimatch.config import get_settings

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    @abstractmethod
    async def upload_file(self, file: UploadFile, folder: str = "avatars") -> dict[str, Any]:
        ...


class LocalStorageProvider(StorageProvider):
    """Store uploaded files on the local filesystem under LOCAL_STORAGE_PATH."""

    def __init__(self):
        self.settings = get_settings()
        self.base_path = Path(self.settings.LOCAL_STORAGE_PATH).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file: UploadFile, folder: str = "avatars") -> dict[str, Any]:
        ext = Path(file.filename or "file.bin").suffix
        filename = f"{uuid.uuid4().hex}{ext}"
        folder_path = self.base_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        dest = folder_path / filename

        contents = await file.read()
        dest.write_bytes(contents)

        public_url = f"{self.settings.STORAGE_PUBLIC_URL}/{folder}/{filename}"
        return {"url": public_url, "path": str(dest)}


class MinioStorageProvider(StorageProvider):
    """MinIO/S3 compatible object storage provider."""

    def __init__(self):
        self.settings = get_settings()
        try:
            from minio import Minio
        except ImportError as exc:
            raise RuntimeError("minio package is required for MinIO storage") from exc

        endpoint = self.settings.MINIO_ENDPOINT or "localhost:9000"
        self.client = Minio(
            endpoint,
            access_key=self.settings.MINIO_ACCESS_KEY or "minioadmin",
            secret_key=self.settings.MINIO_SECRET_KEY or "minioadmin",
            secure=endpoint.startswith("https"),
        )
        self.bucket = self.settings.MINIO_BUCKET
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    async def upload_file(self, file: UploadFile, folder: str = "avatars") -> dict[str, Any]:
        import io

        ext = Path(file.filename or "file.bin").suffix
        filename = f"{folder}/{uuid.uuid4().hex}{ext}"
        data = await file.read()
        self.client.put_object(
            self.bucket,
            filename,
            io.BytesIO(data),
            length=len(data),
            content_type=file.content_type or "application/octet-stream",
        )
        url = f"{self.settings.STORAGE_PUBLIC_URL}/{self.bucket}/{filename}"
        return {"url": url, "path": filename}


class StorageService:
    def __init__(self, provider: StorageProvider | None = None):
        self._provider = provider

    @property
    def provider(self) -> StorageProvider:
        if self._provider is None:
            settings = get_settings()
            if settings.STORAGE_PROVIDER.lower() == "minio":
                self._provider = MinioStorageProvider()
            else:
                self._provider = LocalStorageProvider()
        return self._provider

    async def upload_file(self, file: UploadFile, folder: str = "avatars") -> dict[str, Any]:
        return await self.provider.upload_file(file, folder)
