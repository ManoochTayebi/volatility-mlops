import argparse
import os
from pathlib import Path

from dotenv import load_dotenv


def upload_directory(container, source_dir: Path, prefix: str, relative_root: str) -> int:
    uploaded = 0
    if not source_dir.exists():
        print(f"Skipping missing artifact directory: {source_dir}")
        return uploaded

    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(source_dir).as_posix()
        blob_name = f"{prefix}/{relative_root}/{relative_path}"
        with path.open("rb") as file_obj:
            container.upload_blob(blob_name, file_obj, overwrite=True)
        uploaded += 1
    return uploaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload trained model artifacts to Azure Blob Storage")
    parser.add_argument("--data-root", default="backend/data")
    parser.add_argument("--container", default=os.getenv("AZURE_MODEL_ARTIFACTS_CONTAINER"))
    parser.add_argument("--prefix", default=os.getenv("AZURE_MODEL_ARTIFACTS_PREFIX", "latest"))
    args = parser.parse_args()

    load_dotenv()

    if not args.container:
        raise ValueError("Set AZURE_MODEL_ARTIFACTS_CONTAINER or pass --container")

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING must be set")

    from azure.storage.blob import BlobServiceClient

    client = BlobServiceClient.from_connection_string(connection_string)
    container = client.get_container_client(args.container)
    if not container.exists():
        container.create_container()

    data_root = Path(args.data_root)
    prefix = args.prefix.strip("/")
    uploaded = 0
    uploaded += upload_directory(container, data_root / "nn_models", prefix, "nn_models")
    uploaded += upload_directory(container, data_root / "saved_volatilities", prefix, "saved_volatilities")

    print(f"Uploaded {uploaded} artifact files to Azure Blob container {args.container}/{prefix}")


if __name__ == "__main__":
    main()
