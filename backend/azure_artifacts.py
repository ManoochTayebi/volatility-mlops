"""
Azure Blob artifact helpers for serving-time model refresh.

When AZURE_MODEL_ARTIFACTS_CONTAINER is configured, the app downloads the latest
trained model files from Blob Storage into backend/data before loading models.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _blob_client():
    from azure.storage.blob import BlobServiceClient

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING must be set for Azure artifact download")
    return BlobServiceClient.from_connection_string(connection_string)


def download_artifacts_if_configured(target_root: str | Path = "backend/data") -> None:
    container_name = os.getenv("AZURE_MODEL_ARTIFACTS_CONTAINER")
    if not container_name:
        return

    prefix = os.getenv("AZURE_MODEL_ARTIFACTS_PREFIX", "latest").strip("/")
    target_root = Path(target_root)
    client = _blob_client()
    container = client.get_container_client(container_name)

    downloaded = 0
    for blob in container.list_blobs(name_starts_with=f"{prefix}/"):
        relative = blob.name[len(prefix) + 1 :]
        if not relative:
            continue
        target_path = target_root / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("wb") as file_obj:
            file_obj.write(container.download_blob(blob.name).readall())
        downloaded += 1

    logger.info("Downloaded %s Azure model artifact files from %s/%s", downloaded, container_name, prefix)
