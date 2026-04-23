import tempfile
import unittest
from pathlib import Path

from app import InventoryStore


class InventoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.db_path = base / "test.db"
        self.init_sql_path = Path(__file__).resolve().parents[1] / "db" / "init.sql"
        self.store = InventoryStore(self.db_path, self.init_sql_path)
        self.store.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_is_seeded_with_20_products(self):
        self.assertEqual(20, len(self.store.list_products()))

    def test_can_add_update_and_delete_product(self):
        created = self.store.add_product("Test Product", 7, 10.5)
        self.assertEqual("Test Product", created["name"])

        updated = self.store.update_quantity(created["id"], 3)
        self.assertTrue(updated)

        products = self.store.list_products()
        found = [p for p in products if p["id"] == created["id"]][0]
        self.assertEqual(3, found["quantity"])

        deleted = self.store.delete_product(created["id"])
        self.assertTrue(deleted)

        ids = {p["id"] for p in self.store.list_products()}
        self.assertNotIn(created["id"], ids)


if __name__ == "__main__":
    unittest.main()
