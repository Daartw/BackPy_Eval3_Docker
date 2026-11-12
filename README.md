# Product Service — Backend Python

[![CI](https://github.com/Daartw/BackPy_Eval3_Docker/actions/workflows/ci.yml/badge.svg)](https://github.com/Daartw/BackPy_Eval3_Docker/actions/workflows/ci.yml)

API REST de gestión de productos construida con **Python, Flask y MySQL**, empaquetada con Docker.
Es uno de los tres servicios de una aplicación full stack dockerizada:

| Servicio | Repositorio | Puerto |
|---|---|---|
| Usuarios | [BackJs_Eval3_Docker](https://github.com/Daartw/BackJs_Eval3_Docker) | 8081 |
| Productos (este) | `BackPy_Eval3_Docker` | 8082 |
| Frontend | [Front_Eval3_Docker](https://github.com/Daartw/Front_Eval3_Docker) | 80 |

## Características

- CRUD completo de productos y búsqueda por nombre, precio y stock.
- Lectura pública; escritura protegida con API key.
- Validación de entrada y consultas SQL parametrizadas.
- Servidor de producción **gunicorn**, imagen Docker sin root y con *healthcheck*.
- Pruebas automatizadas, lint con reglas de seguridad y auditoría de dependencias en CI.

## Requisitos

- Python 3.12 o superior
- MySQL 8.0 o superior

## Configuración

```bash
cp .env.example .env
```

| Variable | Descripción |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Conexión a MySQL |
| `PORT` | Puerto del servicio (por defecto 8082) |
| `FLASK_ENV` | `production` exige definir `CORS_ORIGINS` |
| `CORS_ORIGINS` | Orígenes del frontend autorizados, separados por coma |
| `ADMIN_API_KEY` | Clave para crear, editar y eliminar productos (cabecera `X-API-Key`) |
| `FLASK_DEBUG` | `1` activa el modo debug, solo en desarrollo local |

Crea la base de datos y un usuario propio para el servicio (evita usar `root`):

```sql
CREATE DATABASE products_db;
CREATE USER 'products_app'@'%' IDENTIFIED BY 'una_clave_segura';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE ON products_db.* TO 'products_app'@'%';
```

## Ejecutar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

python app.py                      # desarrollo, en http://127.0.0.1:8082
pytest                             # pruebas (no requieren MySQL)
ruff check .                       # lint
```

Con Docker:

```bash
docker build -t backpy_eval3 .
docker run --rm -p 8082:8082 --env-file .env backpy_eval3
```

## Endpoints

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| GET | `/health` | Público | Estado del servicio y de la base de datos |
| GET | `/api/products` | Público | Listar productos |
| GET | `/api/products/{id}` | Público | Obtener un producto |
| GET | `/api/products/search` | Público | Buscar por `name`, `minPrice`, `maxPrice`, `minStock` |
| POST | `/api/products` | `X-API-Key` | Crear un producto |
| PUT | `/api/products/{id}` | `X-API-Key` | Actualizar un producto |
| DELETE | `/api/products/{id}` | `X-API-Key` | Eliminar un producto |

Crear un producto:

```bash
curl -X POST http://localhost:8082/api/products \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -d '{"name":"Laptop HP","description":"Laptop de 15.6 pulgadas","price":899.99,"stock":15,"icon":"💻"}'
```

## Seguridad

Ver [SECURITY.md](SECURITY.md) para las medidas implementadas y cómo reportar una vulnerabilidad.

## Autor

Daniel Araya Rebolledo — [@Daartw](https://github.com/Daartw)
