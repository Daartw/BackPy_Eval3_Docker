"""Las pruebas reemplazan la conexión a MySQL por una base en memoria: no requieren servicios externos."""
import os

os.environ["ADMIN_API_KEY"] = "clave-de-prueba"
os.environ.pop("CORS_ORIGINS", None)

import pytest  # noqa: E402

import app as service  # noqa: E402


class FakeCursor:
    def __init__(self, db, dictionary):
        self.db, self.dictionary = db, dictionary
        self.rows, self.lastrowid, self.rowcount = [], None, 0

    def execute(self, query, params=()):
        self.db.queries.append((" ".join(query.split()), tuple(params)))
        sql = query.strip().upper()
        products = self.db.products
        if sql.startswith("SELECT 1"):
            self.rows = [(1,)]
        elif sql.startswith("SELECT ID FROM PRODUCTS WHERE ID"):
            self.rows = [{"id": params[0]}] if params[0] in products else []
        elif sql.startswith("SELECT * FROM PRODUCTS WHERE ID"):
            self.rows = [dict(products[params[0]])] if params[0] in products else []
        elif sql.startswith("SELECT * FROM PRODUCTS"):
            self.rows = [dict(p) for p in products.values()]
        elif sql.startswith("INSERT"):
            self.lastrowid = max(products, default=0) + 1
            name, description, price, stock, icon = params
            products[self.lastrowid] = {"id": self.lastrowid, "name": name, "description": description,
                                        "price": price, "stock": stock, "icon": icon}
        elif sql.startswith("UPDATE"):
            self.rowcount = 1
        elif sql.startswith("DELETE"):
            self.rowcount = 1 if products.pop(params[0], None) else 0

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def close(self):
        pass


class FakeConnection:
    def __init__(self, db):
        self.db = db

    def cursor(self, dictionary=False):
        return FakeCursor(self.db, dictionary)

    def commit(self):
        self.db.commits += 1

    def close(self):
        self.db.closed += 1


class FakeDatabase:
    def __init__(self):
        self.products, self.queries, self.commits, self.closed = {}, [], 0, 0
        self.available = True


@pytest.fixture
def db(monkeypatch):
    fake = FakeDatabase()
    monkeypatch.setattr(service, "get_db_connection", lambda: FakeConnection(fake) if fake.available else None)
    return fake


@pytest.fixture
def client(db):
    service.app.config.update(TESTING=False)
    return service.app.test_client()


@pytest.fixture
def admin():
    return {"X-API-Key": "clave-de-prueba"}
