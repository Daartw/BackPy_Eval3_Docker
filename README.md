# Backend 2 - Product Service

Backend en Python (Flask) para gestión de productos con base de datos MySQL.

## Características

- API REST para gestión de productos
- CRUD completo de productos
- Búsqueda por nombre, precio y stock
- Base de datos MySQL
- Configuración vía archivo .env

## Requisitos

- Python 3.8 o superior
- MySQL 8.0 o superior
- pip

## Configuración

1. Copiar el archivo de ejemplo:
```bash
cp .env.example .env
```

2. Editar `.env` con sus credenciales de MySQL:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password
DB_NAME=products_db
PORT=8082
```

3. Crear la base de datos en MySQL:
```sql
CREATE DATABASE products_db;
```

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar

```bash
python app.py
```

El servidor iniciará en el puerto 8082.

## Endpoints

- `POST /api/products` - Crear nuevo producto
- `GET /api/products` - Obtener todos los productos
- `GET /api/products/{id}` - Obtener producto por ID
- `GET /api/products/search?name=xxx` - Buscar productos por nombre
- `GET /api/products/search?minPrice=xxx&maxPrice=yyy` - Buscar por rango de precio
- `GET /api/products/search?minStock=xxx` - Buscar por stock mínimo
- `PUT /api/products/{id}` - Actualizar producto
- `DELETE /api/products/{id}` - Eliminar producto

## Ejemplo de Uso

Crear producto:
```bash
curl -X POST http://localhost:8082/api/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Laptop HP","description":"Laptop de 15.6 pulgadas","price":899.99,"stock":15,"icon":"💻"}'
```

Obtener productos:
```bash
curl http://localhost:8082/api/products
```
