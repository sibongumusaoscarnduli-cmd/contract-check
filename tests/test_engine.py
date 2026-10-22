from __future__ import annotations

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from contractcheck.engine import ContractError, _check_schema, load_document, report, run
from contractcheck.fixture import FixtureHandler

ROOT = Path(__file__).resolve().parents[1]


class SchemaChecks(unittest.TestCase):
    def test_required_enum_and_nested_types_are_checked(self):
        document = {"openapi": "3.0.3", "paths": {"/x": {}}, "components": {"schemas": {"Thing": {
            "type": "object", "required": ["state", "count"], "properties": {
                "state": {"type": "string", "enum": ["ready"]}, "count": {"type": "integer", "minimum": 1}
            }
        }}}}
        schema = {"$ref": "#/components/schemas/Thing"}
        self.assertEqual([], _check_schema({"state": "ready", "count": 2}, schema, document))
        issues = _check_schema({"state": "wrong", "count": 0}, schema, document)
        self.assertEqual(2, len(issues))

    def test_missing_required_property_is_reported(self):
        doc = {"openapi": "3.0.3", "paths": {"/x": {}}}
        errors = _check_schema({}, {"type": "object", "required": ["id"]}, doc)
        self.assertIn("response.id: required property is missing", errors)


class RunnerChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.document = load_document(ROOT / "examples" / "orders.openapi.json")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_generated_local_operations_match_contract(self):
        checks = run(self.document, self.url)
        self.assertEqual(3, len(checks))
        self.assertTrue(all(check.passed for check in checks), checks)
        self.assertEqual({200, 201}, {check.actual_status for check in checks})
        self.assertEqual({"total": 3, "passed": 3, "failed": 0}, report(checks)["summary"])

    def test_external_hosts_are_rejected_before_request(self):
        with self.assertRaisesRegex(ContractError, "Safety stop"):
            run(self.document, "https://example.com")

    def test_malformed_document_fails_closed(self):
        path = ROOT / "tests" / "invalid-openapi.json"
        path.write_text('{"openapi":"2.0","paths":{}}', encoding="utf-8")
        try:
            with self.assertRaisesRegex(ContractError, "OpenAPI 3"):
                load_document(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
