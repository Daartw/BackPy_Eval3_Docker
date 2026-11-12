"""Servicio de productos (Flask + MySQL)."""
import decimal
import hmac
import logging
import os
from contextlib import contextmanager
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from mysql.connector import Error
from werkzeug.exceptions import HTTPException

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("products")

app = Flask(__name__)
# Las peticiones de esta API son JSON pequeños: se rechaza cualquier cuerpo mayor a 16 KB.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

IS_PRODUCTION = os.getenv("FLASK_ENV", "development").lower() == "production"
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def _cors_origins():
    """Orígenes autorizados. En producción solo los de CORS_ORIGINS; en desarrollo, cualquiera."""
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if origins:
        return "*" if "*" in origins else origins
    if IS_PRODUCTION:
        log.warning("CORS_ORIGINS no está definido: el navegador bloqueará las peticiones desde otros orígenes.")
        return []
    return "*"


CORS(
    app,
    resources={r"/api/*": {"origins": _cors_origins()}},
    methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
    max_age=600,
)

# Database configuration
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "products_db"),
    "connection_timeout": 10,
}

NAME_MAX = 100
DESCRIPTION_MAX = 2000
ICON_MAX = 50
PRICE_MAX = decimal.Decimal("99999999.99")
STOCK_MAX = 1_000_000_000


class ValidationError(ValueError):
    """Dato de entrada inválido (respuesta 400)."""


class DatabaseUnavailable(RuntimeError):
    """No se pudo usar la base de datos (respuesta 503)."""


def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except Error as exc:
        log.error("Error connecting to MySQL: %s", exc)
        return None


@contextmanager
def db_cursor(dictionary=False, commit=False):
    """Entrega un cursor y garantiza que la conexión se cierre aunque ocurra un error."""
    connection = get_db_connection()
    if not connection:
        raise DatabaseUnavailable()
    cursor = connection.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            connection.commit()
    finally:
        cursor.close()
        connection.close()


def require_api_key(view):
    """Exige la cabecera X-API-Key en las rutas que modifican datos."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not ADMIN_API_KEY:
            return jsonify({"error": "Ruta administrativa deshabilitada: define ADMIN_API_KEY"}), 503
        provided = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided.encode(), ADMIN_API_KEY.encode()):
            return jsonify({"error": "API key inválida o ausente"}), 401
        return view(*args, **kwargs)

    return wrapper


# --- validación ---------------------------------------------------------------
def _text(value, field, max_length, required=False):
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"El campo '{field}' debe ser texto")
    value = value.strip()
    if required and not value:
        raise ValidationError(f"El campo '{field}' es obligatorio")
    if len(value) > max_length:
        raise ValidationError(f"El campo '{field}' admite hasta {max_length} caracteres")
    return value


def _price(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValidationError("El precio debe ser un número")
    try:
        price = decimal.Decimal(str(value))
    except decimal.InvalidOperation:
        raise ValidationError("El precio debe ser un número") from None
    if not price.is_finite() or price < 0 or price > PRICE_MAX:
        raise ValidationError("El precio está fuera del rango permitido")
    return price.quantize(decimal.Decimal("0.01"))


def _stock(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("El stock debe ser un número entero")
    if value < 0 or value > STOCK_MAX:
        raise ValidationError("El stock está fuera del rango permitido")
    return value


def validate_product(data, partial=False):
    """Valida y normaliza un producto. Con partial=True solo revisa los campos enviados."""
    if not isinstance(data, dict):
        raise ValidationError("Se esperaba un objeto JSON")
    if not partial:
        missing = [f for f in ("name", "price", "stock") if f not in data]
        if missing:
            raise ValidationError("Faltan campos requeridos")
    clean = {}
    if "name" in data:
        clean["name"] = _text(data["name"], "name", NAME_MAX, required=True)
    if "description" in data or not partial:
        clean["description"] = _text(data.get("description"), "description", DESCRIPTION_MAX)
    if "price" in data:
        clean["price"] = _price(data["price"])
    if "stock" in data:
        clean["stock"] = _stock(data["stock"])
    if "icon" in data or not partial:
        clean["icon"] = _text(data.get("icon"), "icon", ICON_MAX)
    return clean


def _query_number(name, cast):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return None
    try:
        value = cast(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"El parámetro '{name}' debe ser numérico") from None
    if value != value or value in (float("inf"), float("-inf")):  # NaN o infinito
        raise ValidationError(f"El parámetro '{name}' debe ser numérico")
    return value


def _serialize(product):
    if isinstance(product.get("price"), decimal.Decimal):
        product["price"] = float(product["price"])
    return product


# --- base de datos ------------------------------------------------------------
def init_db():
    with db_cursor(commit=True) as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                stock INT NOT NULL,
                icon VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Check if table is empty and seed if necessary
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        if count == 0:
            log.info("Seeding initial products...")
            initial_products = [
                ("Laptop HP Pavilion", "Laptop de 15.6 pulgadas, Intel Core i5, 8GB RAM, 256GB SSD", 899.99, 15, "💻"),
                ("Smartphone Samsung Galaxy", "Samsung Galaxy S23, 128GB, cámara de 50MP, 5G", 799.99, 25, "📱"),
                ("Auriculares Sony WH-1000XM4", "Auriculares inalámbricos con cancelación de ruido", 349.99, 30, "🎧"),
                ("Tablet iPad Air", "Apple iPad Air 5ta generación, 64GB, Wi-Fi", 599.99, 20, "📲"),
                ("Smartwatch Apple Watch", "Apple Watch Series 8, GPS, 45mm", 449.99, 18, "⌚"),
                ("Cámara Canon EOS", "Cámara DSLR Canon EOS Rebel T7, 24.1MP", 549.99, 12, "📷"),
                ("Consola PlayStation 5", "Sony PlayStation 5, 825GB SSD, con control DualSense", 499.99, 8, "🎮"),
                ("Monitor Dell UltraSharp", "Monitor Dell 27 pulgadas 4K, IPS, USB-C", 429.99, 22, "🖥️"),
            ]
            cursor.executemany("""
                INSERT INTO products (name, description, price, stock, icon)
                VALUES (%s, %s, %s, %s, %s)
            """, initial_products)
            log.info("Initial products seeded successfully")
    log.info("Products table ready")


# --- cabeceras y errores --------------------------------------------------------
@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    return response


@app.errorhandler(ValidationError)
def handle_validation(error):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(DatabaseUnavailable)
def handle_db_unavailable(_error):
    return jsonify({"error": "Error de conexión a la base de datos"}), 503


@app.errorhandler(Error)
def handle_db_error(error):
    log.error("Error de base de datos: %s", error)
    return jsonify({"error": "Error interno del servidor"}), 500


@app.errorhandler(HTTPException)
def handle_http(error):
    return jsonify({"error": error.description}), error.code


@app.errorhandler(Exception)
def handle_unexpected(error):
    # El detalle queda en el log; al cliente no se le entrega información interna.
    log.exception("Error no controlado: %s", error)
    return jsonify({"error": "Error interno del servidor"}), 500


# --- rutas ------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    with db_cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return jsonify({"status": "ok"})


@app.route("/api/products", methods=["GET"])
def get_all_products():
    with db_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
    return jsonify([_serialize(p) for p in products])


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    with db_cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
    if not product:
        return jsonify({"error": "Producto no encontrado"}), 404
    return jsonify(_serialize(product))


@app.route("/api/products", methods=["POST"])
@require_api_key
def create_product():
    data = validate_product(request.get_json(silent=True))
    with db_cursor(commit=True) as cursor:
        cursor.execute(
            """
            INSERT INTO products (name, description, price, stock, icon)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (data["name"], data["description"], data["price"], data["stock"], data["icon"]),
        )
        product_id = cursor.lastrowid
    return jsonify({"id": product_id, "message": "Producto creado exitosamente"}), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@require_api_key
def update_product(product_id):
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "No se proporcionaron datos"}), 400
    data = validate_product(payload, partial=True)

    with db_cursor(commit=True) as cursor:
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Producto no encontrado"}), 404
        if data:
            # Los nombres de columna vienen de una lista fija (validate_product); los valores van parametrizados.
            assignments = ", ".join(f"{column} = %s" for column in data)
            cursor.execute(
                f"UPDATE products SET {assignments} WHERE id = %s",  # noqa: S608 (columnas de lista fija)
                [*data.values(), product_id],
            )
    return jsonify({"message": "Producto actualizado exitosamente"})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@require_api_key
def delete_product(product_id):
    with db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        deleted = cursor.rowcount
    if deleted == 0:
        return jsonify({"error": "Producto no encontrado"}), 404
    return jsonify({"message": "Producto eliminado exitosamente"})


@app.route("/api/products/search", methods=["GET"])
def search_products():
    name = request.args.get("name")
    min_price = _query_number("minPrice", float)
    max_price = _query_number("maxPrice", float)
    min_stock = _query_number("minStock", int)

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if name:
        query += " AND name LIKE %s"
        params.append(f"%{name[:NAME_MAX]}%")
    if min_price is not None:
        query += " AND price >= %s"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= %s"
        params.append(max_price)
    if min_stock is not None:
        query += " AND stock > %s"
        params.append(min_stock)

    with db_cursor(dictionary=True) as cursor:
        cursor.execute(query, params)
        products = cursor.fetchall()
    return jsonify([_serialize(p) for p in products])


if __name__ == "__main__":
    # Servidor de desarrollo. En producción se usa gunicorn (ver Dockerfile y wsgi.py).
    # El modo debug expone una consola que ejecuta código: solo se activa con FLASK_DEBUG=1
    # y nunca debe usarse en un servidor accesible desde la red.
    init_db()
    port = int(os.getenv("PORT", 8082))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    host = os.getenv("HOST", "127.0.0.1")
    log.info("Backend 2 (Product Service) running on port %s", port)
    app.run(host=host, port=port, debug=debug)
