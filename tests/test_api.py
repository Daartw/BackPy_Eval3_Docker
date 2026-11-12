import decimal

import pytest

import app as service

VALID = {"name": "Teclado", "description": "Mecánico", "price": 49.99, "stock": 5, "icon": "⌨️"}


def test_lectura_publica_y_precio_como_numero(client, db):
    db.products[1] = {"id": 1, "name": "Teclado", "description": "", "price": decimal.Decimal("49.99"),
                      "stock": 5, "icon": ""}
    response = client.get("/api/products")
    assert response.status_code == 200
    assert response.get_json()[0]["price"] == 49.99
    assert client.get("/api/products/1").status_code == 200
    assert client.get("/api/products/99").status_code == 404


@pytest.mark.parametrize("method,path", [
    ("post", "/api/products"), ("put", "/api/products/1"), ("delete", "/api/products/1"),
])
def test_escritura_exige_api_key(client, db, method, path):
    assert getattr(client, method)(path, json=VALID).status_code == 401
    assert getattr(client, method)(path, json=VALID, headers={"X-API-Key": "incorrecta"}).status_code == 401
    assert db.products == {} and db.commits == 0


def test_sin_clave_configurada_la_escritura_queda_cerrada(client, db, monkeypatch):
    monkeypatch.setattr(service, "ADMIN_API_KEY", "")
    assert client.post("/api/products", json=VALID, headers={"X-API-Key": ""}).status_code == 503
    assert db.products == {}


def test_crear_actualizar_y_eliminar(client, db, admin):
    created = client.post("/api/products", json=VALID, headers=admin)
    assert created.status_code == 201
    product_id = created.get_json()["id"]
    assert db.products[product_id]["price"] == decimal.Decimal("49.99")

    assert client.put(f"/api/products/{product_id}", json={"stock": 9}, headers=admin).status_code == 200
    assert client.put("/api/products/999", json={"stock": 9}, headers=admin).status_code == 404
    assert client.delete(f"/api/products/{product_id}", headers=admin).status_code == 200
    assert client.delete(f"/api/products/{product_id}", headers=admin).status_code == 404


@pytest.mark.parametrize("payload", [
    {"name": "Sin precio", "stock": 1},
    {**VALID, "name": ""},
    {**VALID, "name": "x" * 101},
    {**VALID, "name": {"$ne": ""}},
    {**VALID, "price": -1},
    {**VALID, "price": "gratis"},
    {**VALID, "price": "NaN"},
    {**VALID, "price": True},
    {**VALID, "stock": 1.5},
    {**VALID, "stock": -3},
    {**VALID, "icon": "x" * 51},
    ["no", "es", "objeto"],
])
def test_entrada_invalida_devuelve_400(client, db, admin, payload):
    response = client.post("/api/products", json=payload, headers=admin)
    assert response.status_code == 400
    assert "error" in response.get_json()
    assert db.products == {}


def test_actualizar_solo_usa_columnas_conocidas(client, db, admin):
    db.products[1] = dict(VALID, id=1)
    response = client.put("/api/products/1", json={"stock": 2, "id = 1; DROP TABLE products; --": 1}, headers=admin)
    assert response.status_code == 200
    update = next(q for q, _ in db.queries if q.startswith("UPDATE"))
    assert update == "UPDATE products SET stock = %s WHERE id = %s"


def test_busqueda_parametrizada_y_validada(client, db):
    assert client.get("/api/products/search?minPrice=abc").status_code == 400
    assert client.get("/api/products/search?minStock=1.5").status_code == 400
    assert client.get("/api/products/search?minPrice=nan").status_code == 400
    injection = "' OR '1'='1"
    assert client.get("/api/products/search", query_string={"name": injection, "maxPrice": "10"}).status_code == 200
    query, params = db.queries[-1]
    assert injection not in query
    assert params == (f"%{injection}%", 10.0)


def test_errores_no_filtran_detalles_internos(client, db, monkeypatch):
    db.available = False
    response = client.get("/api/products")
    assert response.status_code == 503
    assert response.get_json() == {"error": "Error de conexión a la base de datos"}

    def boom():
        raise RuntimeError("password=secreto host=10.0.0.5")

    monkeypatch.setattr(service, "get_db_connection", boom)
    response = client.get("/api/products")
    assert response.status_code == 500
    assert "secreto" not in response.get_data(as_text=True)


def test_la_conexion_se_cierra_aunque_falle_la_consulta(client, db, admin):
    client.post("/api/products", json={**VALID, "price": "gratis"}, headers=admin)
    client.get("/api/products")
    client.get("/api/products/search?minPrice=abc")
    assert db.closed == 1  # solo la consulta que llegó a abrir conexión, y quedó cerrada


def test_cabeceras_de_seguridad_y_rutas_desconocidas(client, db):
    response = client.get("/no-existe")
    assert response.status_code == 404
    assert response.get_json()["error"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert client.get("/health").get_json() == {"status": "ok"}


def test_el_modo_debug_no_esta_activo_por_defecto():
    assert service.app.debug is False
