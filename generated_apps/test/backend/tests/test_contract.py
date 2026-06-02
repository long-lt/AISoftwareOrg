from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackendContractTest(unittest.TestCase):
    def test_routes_match_feature_contract(self) -> None:
        source = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
        self.assertIn('/health', source)
        self.assertIn('/api/todo', source)
        self.assertIn('def list_todo', source)
        self.assertIn('def create_todo', source)
        self.assertIn('/api/dashboard', source)
        self.assertIn('def list_dashboard', source)
        self.assertIn('def create_dashboard', source)
        self.assertIn('/api/settings', source)
        self.assertIn('def list_settings', source)
        self.assertIn('def create_settings', source)

    def test_database_schema_contains_contract_entities(self) -> None:
        schema = (ROOT.parent / 'docs' / 'database_schema.sql').read_text(encoding='utf-8')
        self.assertIn('CREATE TABLE IF NOT EXISTS todo_items', schema)
        self.assertIn('CREATE TABLE IF NOT EXISTS dashboard_items', schema)
        self.assertIn('CREATE TABLE IF NOT EXISTS settings_items', schema)

    def test_openapi_contains_contract_paths(self) -> None:
        openapi = (ROOT.parent / 'docs' / 'openapi.yaml').read_text(encoding='utf-8')
        self.assertIn('/health:', openapi)
        self.assertIn('/api/todo:', openapi)
        self.assertIn('/api/dashboard:', openapi)
        self.assertIn('/api/settings:', openapi)


if __name__ == '__main__':
    unittest.main()
