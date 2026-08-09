import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import config_store, sources_store, document_store


class TestStores(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

        # Patch paths to point to temp directory
        self.config_patch = patch.object(config_store, "CONFIG_STORE_PATH", self.tmp_path / "config_store.json")
        self.config_example_patch = patch.object(config_store, "CONFIG_STORE_EXAMPLE_PATH", self.tmp_path / "config_store.json.example")
        self.sources_patch = patch.object(sources_store, "SOURCES_STORE_PATH", self.tmp_path / "sources_store.json")
        self.docs_patch = patch.object(document_store, "DOCUMENTS_STORE_PATH", self.tmp_path / "documents_store.json")

        self.config_patch.start()
        self.config_example_patch.start()
        self.sources_patch.start()
        self.docs_patch.start()

        # Seed example config store
        example_data = [
            {
                "key": "test_model_1",
                "group": "test_model",
                "description": "Model 1",
                "value": "model-v1",
                "is_secret": False,
                "is_active": True,
            }
        ]
        with open(self.tmp_path / "config_store.json.example", "w", encoding="utf-8") as f:
            json.dump(example_data, f)

    def tearDown(self):
        self.config_patch.stop()
        self.config_example_patch.stop()
        self.sources_patch.stop()
        self.docs_patch.stop()
        self.tmp_dir.cleanup()

    def test_config_store_lifecycle(self):
        # 1. Read initialized active value
        active_val = config_store.get_active_value("test_model")
        self.assertEqual(active_val, "model-v1")

        # 2. Add second candidate
        new_entry = config_store.create_config(
            group="test_model",
            description="Model 2",
            value="model-v2",
            is_secret=False,
        )
        self.assertFalse(new_entry["is_active"])

        # 3. Activate second candidate
        config_store.set_active(new_entry["key"])
        self.assertEqual(config_store.get_active_value("test_model"), "model-v2")

        # 4. Attempt deleting the only remaining entry should fail
        # First delete entry 1
        config_store.delete_config("test_model_1")
        # Now only new_entry remains; deleting it must raise ValueError
        with self.assertRaises(ValueError):
            config_store.delete_config(new_entry["key"])

    def test_sources_store_lifecycle(self):
        # 1. Create source
        src = sources_store.create_source(
            category_name="Overview Box",
            onedrive_url="https://example.com/box.xlsx",
        )
        self.assertEqual(src["sync_status"], "never_synced")

        # 2. Mark synced
        synced = sources_store.mark_synced(src["id"], chunk_count=42, fetch_method="fallback_download")
        self.assertEqual(synced["sync_status"], "success")
        self.assertEqual(synced["chunk_count"], 42)

        # 3. Update URL resets status
        updated = sources_store.update_source(src["id"], onedrive_url="https://example.com/new_box.xlsx")
        self.assertEqual(updated["sync_status"], "never_synced")

    def test_document_store_lifecycle(self):
        entry = document_store.register_document(
            filename="test_doc.pdf",
            label="Test Document",
            file_type="pdf",
            chunk_count=10,
            is_active=True,
        )
        self.assertIn("test_doc.pdf", document_store.get_active_filenames())

        # Toggle inactive
        document_store.toggle_active("test_doc.pdf", is_active=False)
        self.assertNotIn("test_doc.pdf", document_store.get_active_filenames())


if __name__ == "__main__":
    unittest.main()
