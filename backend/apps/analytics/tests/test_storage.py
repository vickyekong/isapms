import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.analytics.storage import ArtifactUnavailable, load_artifact, save_artifact

BUNDLE = {"model": "stub", "features": ["ca_score"]}


class ArtifactStorageTests(SimpleTestCase):
    def setUp(self):
        self.work_dir = Path(tempfile.mkdtemp())
        self.bundled_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work_dir, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.bundled_dir, ignore_errors=True)
        settings_override = override_settings(MODEL_ARTIFACT_DIR=self.work_dir, BUNDLED_ARTIFACT_DIR=self.bundled_dir)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def _env(self, **values):
        cleared = {"BLOB_READ_WRITE_TOKEN": "", "VERCEL_BLOB_READ_WRITE_TOKEN": "", **values}
        return mock.patch.dict(os.environ, cleared)

    def test_local_storage_without_blob_token(self):
        with self._env():
            artifact_path = save_artifact(BUNDLE, "dt-local")
            self.assertEqual(artifact_path, str(self.work_dir / "dt-local.joblib"))
            self.assertEqual(load_artifact(artifact_path), BUNDLE)

    def test_path_from_another_machine_falls_back_to_bundled_copy(self):
        with self._env():
            save_artifact(BUNDLE, "dt-shipped")
            shutil.move(self.work_dir / "dt-shipped.joblib", self.bundled_dir / "dt-shipped.joblib")
            self.assertEqual(load_artifact("/Users/someone/isapms/backend/artifacts/dt-shipped.joblib"), BUNDLE)

    def test_missing_file_raises(self):
        with self._env(), self.assertRaises(ArtifactUnavailable):
            load_artifact("/nowhere/dt-missing.joblib")

    def test_blob_upload_and_cached_download(self):
        remote = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        url = "https://store.private.blob.vercel-storage.com/models/dt-blob.joblib"

        def fake_upload(local_path, path, **kwargs):
            self.assertEqual(path, "models/dt-blob.joblib")
            self.assertEqual(kwargs["access"], "private")
            shutil.copy(local_path, remote / "dt-blob.joblib")
            return SimpleNamespace(url=url)

        def fake_download(url_or_path, local_path, **kwargs):
            self.assertEqual(kwargs["access"], "private")
            shutil.copy(remote / "dt-blob.joblib", local_path)
            return str(local_path)

        with self._env(BLOB_READ_WRITE_TOKEN="test-token"), mock.patch(
            "vercel.blob.upload_file", side_effect=fake_upload
        ), mock.patch("vercel.blob.download_file", side_effect=fake_download) as download:
            artifact_path = save_artifact(BUNDLE, "dt-blob")
            self.assertEqual(artifact_path, url)

            (self.work_dir / "dt-blob.joblib").unlink()
            self.assertEqual(load_artifact(artifact_path), BUNDLE)
            self.assertEqual(load_artifact(artifact_path), BUNDLE)
            self.assertEqual(download.call_count, 1)

    def test_blob_reference_without_token_raises(self):
        with self._env(), self.assertRaises(ArtifactUnavailable):
            load_artifact("https://store.private.blob.vercel-storage.com/models/dt-gone.joblib")
