import unittest
from starlette.testclient import TestClient

from app.main import app


class TestAPIRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("vector_store", data)
        self.assertIn("ai_configuration", data)
        self.assertIn("uptime_seconds", data)

    def test_get_config_endpoint(self):
        response = self.client.get("/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        for item in data:
            if item.get("is_secret"):
                self.assertEqual(item.get("value"), "••••••••")

    def test_get_sources_endpoint(self):
        response = self.client.get("/sources")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_get_documents_endpoint(self):
        response = self.client.get("/documents")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
