import json
import sqlite3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "inventory.db"
INIT_SQL_PATH = BASE_DIR / "db" / "init.sql"
STATIC_DIR = BASE_DIR / "static"


class InventoryStore:
    def __init__(self, db_path: Path, init_sql_path: Path):
        self.db_path = db_path
        self.init_sql_path = init_sql_path

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity >= 0),
                    price REAL NOT NULL CHECK (price >= 0)
                )
                """
            )
            count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if count == 0:
                conn.executescript(self.init_sql_path.read_text(encoding="utf-8"))
            conn.commit()

    def list_products(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, quantity, price FROM products ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def add_product(self, name: str, quantity: int, price: float):
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO products (name, quantity, price) VALUES (?, ?, ?)",
                (name, quantity, price),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, name, quantity, price FROM products WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row)

    def update_quantity(self, product_id: int, quantity: int):
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE products SET quantity = ? WHERE id = ?",
                (quantity, product_id),
            )
            conn.commit()
        return cursor.rowcount > 0

    def delete_product(self, product_id: int):
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
        return cursor.rowcount > 0


STORE = InventoryStore(DB_PATH, INIT_SQL_PATH)


class InventoryHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, message, status=400):
        self._send_json({"error": message}, status)

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        body = self.rfile.read(length).decode("utf-8")
        if not body:
            return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/products":
            self._send_json(STORE.list_products())
            return
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/products":
            self.send_error(404)
            return

        payload = self._read_json_body()
        if payload is None:
            self._send_error("Invalid JSON payload")
            return

        name = str(payload.get("name", "")).strip()
        quantity = payload.get("quantity")
        price = payload.get("price")

        if not name:
            self._send_error("name is required")
            return

        try:
            quantity = int(quantity)
            price = float(price)
            if quantity < 0 or price < 0:
                raise ValueError
        except (TypeError, ValueError):
            self._send_error("quantity and price must be non-negative numbers")
            return

        self._send_json(STORE.add_product(name, quantity, price), status=201)

    def do_PATCH(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/products/"):
            self.send_error(404)
            return

        product_id = path.rsplit("/", 1)[-1]
        if not product_id.isdigit():
            self.send_error(404)
            return

        payload = self._read_json_body()
        if payload is None:
            self._send_error("Invalid JSON payload")
            return

        try:
            quantity = int(payload.get("quantity"))
            if quantity < 0:
                raise ValueError
        except (TypeError, ValueError):
            self._send_error("quantity must be a non-negative integer")
            return

        if not STORE.update_quantity(int(product_id), quantity):
            self._send_error("Product not found", status=404)
            return

        self._send_json({"ok": True})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/products/"):
            self.send_error(404)
            return

        product_id = path.rsplit("/", 1)[-1]
        if not product_id.isdigit():
            self.send_error(404)
            return

        if not STORE.delete_product(int(product_id)):
            self._send_error("Product not found", status=404)
            return

        self.send_response(204)
        self.end_headers()


def run_server(host="127.0.0.1", port=8000):
    STORE.init_db()
    server = ThreadingHTTPServer((host, port), InventoryHandler)
    print(f"Inventory app running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
