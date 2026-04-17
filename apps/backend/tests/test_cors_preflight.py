import unittest

from fastapi.testclient import TestClient

from app.main import app


class CorsPreflightTestCase(unittest.TestCase):
    def test_sources_preflight_allows_localhost_varying_port(self) -> None:
        with TestClient(app) as client:
            response = client.options(
                "/sources",
                headers={
                    "Origin": "http://localhost:55000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("http://localhost:55000", response.headers.get("access-control-allow-origin"))
        self.assertIn("POST", response.headers.get("access-control-allow-methods", ""))

    def test_sources_preflight_allows_loopback_varying_port(self) -> None:
        with TestClient(app) as client:
            response = client.options(
                "/sources",
                headers={
                    "Origin": "http://127.0.0.1:55001",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual("http://127.0.0.1:55001", response.headers.get("access-control-allow-origin"))
        self.assertIn("POST", response.headers.get("access-control-allow-methods", ""))

    def test_sources_preflight_still_rejects_untrusted_origin(self) -> None:
        with TestClient(app) as client:
            response = client.options(
                "/sources",
                headers={
                    "Origin": "http://malicious.example.com",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

        self.assertEqual(400, response.status_code)


if __name__ == "__main__":
    unittest.main()
