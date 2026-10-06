"""
Object Storage Abstraction Service
Supports Amazon S3 storage with graceful local fallback for development.
Used for non-transactional application data (knowledge base documents, ML artifacts, exported files).
"""

import abc
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import BotoCoreError, ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class ObjectStorage(abc.ABC):
    """Abstract base class for object storage"""

    @abc.abstractmethod
    async def upload_bytes(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        """Upload raw bytes to storage"""
        pass

    @abc.abstractmethod
    async def upload_file(
        self, key: str, file_path: Union[str, Path], content_type: Optional[str] = None
    ) -> str:
        """Upload local file to storage"""
        pass

    @abc.abstractmethod
    async def download_bytes(self, key: str) -> bytes:
        """Download object content as bytes"""
        pass

    @abc.abstractmethod
    async def download_file(self, key: str, destination_path: Union[str, Path]) -> bool:
        """Download object to local file path"""
        pass

    @abc.abstractmethod
    async def list_objects(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """List objects matching optional prefix"""
        pass

    @abc.abstractmethod
    async def delete_object(self, key: str) -> bool:
        """Delete object by key"""
        pass


class S3Storage(ObjectStorage):
    """Amazon S3 implementation of ObjectStorage"""

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        prefix: str = "",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.prefix = prefix.strip("/")
        if self.prefix:
            self.prefix += "/"

        self._client = None
        if BOTO3_AVAILABLE:
            try:
                boto_config = BotoConfig(
                    region_name=self.region_name,
                    connect_timeout=5,
                    read_timeout=15,
                    retries={"max_attempts": 3, "mode": "standard"},
                )
                kwargs: Dict[str, Any] = {"config": boto_config}
                if access_key and secret_key:
                    kwargs["aws_access_key_id"] = access_key
                    kwargs["aws_secret_access_key"] = secret_key

                self._client = boto3.client("s3", **kwargs)
                logger.info(f"S3Storage initialized (bucket={self.bucket_name}, region={self.region_name})")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 boto3 client: {e}")

    def _full_key(self, key: str) -> str:
        key = key.lstrip("/")
        return f"{self.prefix}{key}" if self.prefix and not key.startswith(self.prefix) else key

    async def upload_bytes(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        if not self._client:
            raise RuntimeError("S3 client is not available")
        full_key = self._full_key(key)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        def _put():
            self._client.put_object(
                Bucket=self.bucket_name, Key=full_key, Body=data, **extra_args
            )

        await asyncio.to_thread(_put)
        return f"s3://{self.bucket_name}/{full_key}"

    async def upload_file(
        self, key: str, file_path: Union[str, Path], content_type: Optional[str] = None
    ) -> str:
        if not self._client:
            raise RuntimeError("S3 client is not available")
        full_key = self._full_key(key)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        def _upload() -> None:
            if self._client:
                self._client.upload_file(
                    str(file_path), self.bucket_name, full_key, ExtraArgs=extra_args or None
                )

        await asyncio.to_thread(_upload)
        return f"s3://{self.bucket_name}/{full_key}"

    async def download_bytes(self, key: str) -> bytes:
        if not self._client:
            raise RuntimeError("S3 client is not available")
        full_key = self._full_key(key)

        def _get():
            res = self._client.get_object(Bucket=self.bucket_name, Key=full_key)
            return res["Body"].read()

        return await asyncio.to_thread(_get)

    async def download_file(self, key: str, destination_path: Union[str, Path]) -> bool:
        if not self._client:
            return False
        full_key = self._full_key(key)
        dest = Path(destination_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        def _download():
            self._client.download_file(self.bucket_name, full_key, str(dest))

        try:
            await asyncio.to_thread(_download)
            return True
        except Exception as e:
            logger.error(f"Failed to download S3 key '{full_key}': {e}")
            return False

    async def list_objects(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        search_prefix = self._full_key(prefix or "")

        def _list():
            res = self._client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=search_prefix
            )
            contents = res.get("Contents", [])
            return [
                {
                    "key": item["Key"],
                    "size": item["Size"],
                    "last_modified": item["LastModified"].isoformat(),
                }
                for item in contents
            ]

        try:
            return await asyncio.to_thread(_list)
        except Exception as e:
            logger.error(f"S3 list_objects error: {e}")
            return []

    async def delete_object(self, key: str) -> bool:
        if not self._client:
            return False
        full_key = self._full_key(key)

        def _delete():
            self._client.delete_object(Bucket=self.bucket_name, Key=full_key)

        try:
            await asyncio.to_thread(_delete)
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 object '{full_key}': {e}")
            return False


class LocalFileStorage(ObjectStorage):
    """Local filesystem fallback implementation for development"""

    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        self.base_dir = Path(base_dir or "./data/storage")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalFileStorage initialized (dir={self.base_dir.resolve()})")

    def _get_path(self, key: str) -> Path:
        key = key.lstrip("/\\")
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def upload_bytes(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        path = self._get_path(key)
        path.write_bytes(data)
        return f"file://{path.resolve()}"

    async def upload_file(
        self, key: str, file_path: Union[str, Path], content_type: Optional[str] = None
    ) -> str:
        path = self._get_path(key)
        src = Path(file_path)
        path.write_bytes(src.read_bytes())
        return f"file://{path.resolve()}"

    async def download_bytes(self, key: str) -> bytes:
        path = self._get_path(key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key '{key}' not found locally")
        return path.read_bytes()

    async def download_file(self, key: str, destination_path: Union[str, Path]) -> bool:
        try:
            data = await self.download_bytes(key)
            dest = Path(destination_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return True
        except Exception as e:
            logger.error(f"Local download failed: {e}")
            return False

    async def list_objects(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        search_dir = self.base_dir
        if prefix:
            search_dir = self.base_dir / prefix.lstrip("/\\")

        if not search_dir.exists():
            return []

        for root, _, files in os.walk(search_dir):
            for file in files:
                full_p = Path(root) / file
                rel_k = str(full_p.relative_to(self.base_dir)).replace("\\", "/")
                stat = full_p.stat()
                results.append(
                    {
                        "key": rel_k,
                        "size": stat.st_size,
                        "last_modified": str(stat.st_mtime),
                    }
                )
        return results

    async def delete_object(self, key: str) -> bool:
        path = self._get_path(key)
        if path.exists():
            path.unlink()
            return True
        return False


def get_storage_service() -> ObjectStorage:
    """Factory to get configured storage service (S3 in production, Local in dev)"""
    bucket = settings.AWS_S3_BUCKET
    if bucket and BOTO3_AVAILABLE:
        return S3Storage(
            bucket_name=bucket,
            region_name=settings.AWS_REGION,
            prefix=settings.AWS_S3_PREFIX,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return LocalFileStorage()
