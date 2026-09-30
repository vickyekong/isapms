import logging
import os
from pathlib import Path

import joblib
from django.conf import settings

logger = logging.getLogger(__name__)

BLOB_PREFIX = "models/"


class ArtifactUnavailable(Exception):
    pass


def blob_enabled():
    return bool(os.getenv("BLOB_READ_WRITE_TOKEN") or os.getenv("VERCEL_BLOB_READ_WRITE_TOKEN"))


def is_blob_reference(artifact_path):
    return artifact_path.startswith("https://") or artifact_path.startswith(BLOB_PREFIX)


def save_artifact(bundle, version):
    """Write the bundle locally and, when a Blob store is connected, upload it as a private blob.

    Returns the value to store in ModelVersion.artifact_path.
    """
    artifact_dir = Path(settings.MODEL_ARTIFACT_DIR)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    local_path = artifact_dir / f"{version}.joblib"
    joblib.dump(bundle, local_path)
    if not blob_enabled():
        return str(local_path)

    from vercel.blob import upload_file

    result = upload_file(
        local_path,
        f"{BLOB_PREFIX}{version}.joblib",
        access="private",
        content_type="application/octet-stream",
        overwrite=True,
    )
    return result.url


def load_artifact(artifact_path):
    return joblib.load(_resolve(artifact_path))


def _resolve(artifact_path):
    filename = Path(artifact_path).name
    if is_blob_reference(artifact_path):
        cached = Path(settings.MODEL_ARTIFACT_DIR) / filename
        if cached.exists():
            return cached
        if not blob_enabled():
            raise ArtifactUnavailable("The model is stored in Vercel Blob but no Blob token is configured.")
        from vercel.blob import download_file

        try:
            download_file(artifact_path, cached, access="private")
        except Exception as exc:
            logger.exception("Could not download model artifact %s", filename)
            raise ArtifactUnavailable("The model file could not be downloaded.") from exc
        return cached

    # Paths recorded on another machine still resolve if the file ships with the code.
    for candidate in (Path(artifact_path), Path(settings.MODEL_ARTIFACT_DIR) / filename, settings.BUNDLED_ARTIFACT_DIR / filename):
        if candidate.exists():
            return candidate
    raise ArtifactUnavailable("The model file is missing.")
