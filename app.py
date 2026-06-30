from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
import decimal

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'products_db')
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    connection = get_db_connection()
    if connection:
        cursor = connection.cursor()
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
        connection.commit()
        
        # Check if table is empty and seed if necessary
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        if count == 0:
            print("Seeding initial products...")
            initial_products = [
                ("Laptop HP Pavilion", "Laptop de 15.6 pulgadas, Intel Core i5, 8GB RAM, 256GB SSD", 899.99, 15, "💻"),
                ("Smartphone Samsung Galaxy", "Samsung Galaxy S23, 128GB, cámara de 50MP, 5G", 799.99, 25, "📱"),
                ("Auriculares Sony WH-1000XM4", "Auriculares inalámbricos con cancelación de ruido", 349.99, 30, "🎧"),
                ("Tablet iPad Air", "Apple iPad Air 5ta generación, 64GB, Wi-Fi", 599.99, 20, "📲"),
                ("Smartwatch Apple Watch", "Apple Watch Series 8, GPS, 45mm", 449.99, 18, "⌚"),
                ("Cámara Canon EOS", "Cámara DSLR Canon EOS Rebel T7, 24.1MP", 549.99, 12, "📷"),
                ("Consola PlayStation 5", "Sony PlayStation 5, 825GB SSD, con control DualSense", 499.99, 8, "🎮"),
                ("Monitor Dell UltraSharp", "Monitor Dell 27 pulgadas 4K, IPS, USB-C", 429.99, 22, "🖥️")
            ]
            cursor.executemany("""
                INSERT INTO products (name, description, price, stock, icon)
                VALUES (%s, %s, %s, %s, %s)
            """, initial_products)
            connection.commit()
            print("Initial products seeded successfully")
            
        cursor.close()
        connection.close()
        print("Products table ready")

@app.route('/api/products', methods=['GET'])
def get_all_products():
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    cursor.close()
    connection.close()
    
    # Convert Decimal to float for JSON serialization
    for product in products:
        if 'price' in product and isinstance(product['price'], decimal.Decimal):
            product['price'] = float(product['price'])
    
    return jsonify(products)

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404
    
    if 'price' in product and isinstance(product['price'], decimal.Decimal):
        product['price'] = float(product['price'])
    
    return jsonify(product)

@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()
    
    if not data or 'name' not in data or 'price' not in data or 'stock' not in data:
        return jsonify({'error': 'Faltan campos requeridos'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO products (name, description, price, stock, icon)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (data['name'], data.get('description', ''), data['price'], data['stock'], data.get('icon', ''))
    )
    connection.commit()
    product_id = cursor.lastrowid
    cursor.close()
    connection.close()
    
    return jsonify({'id': product_id, 'message': 'Producto creado exitosamente'}), 201

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No se proporcionaron datos'}), 400
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        connection.close()
        return jsonify({'error': 'Producto no encontrado'}), 404
    
    update_fields = []
    update_values = []
    
    if 'name' in data:
        update_fields.append("name = %s")
        update_values.append(data['name'])
    if 'description' in data:
        update_fields.append("description = %s")
        update_values.append(data['description'])
    if 'price' in data:
        update_fields.append("price = %s")
        update_values.append(data['price'])
    if 'stock' in data:
        update_fields.append("stock = %s")
        update_values.append(data['stock'])
    if 'icon' in data:
        update_fields.append("icon = %s")
        update_values.append(data['icon'])
    
    if update_fields:
        update_values.append(product_id)
        cursor.execute(
            f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s",
            update_values
        )
        connection.commit()
    
    cursor.close()
    connection.close()
    
    return jsonify({'message': 'Producto actualizado exitosamente'})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    cursor = connection.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
    
    if cursor.rowcount == 0:
        cursor.close()
        connection.close()
        return jsonify({'error': 'Producto no encontrado'}), 404
    
    connection.commit()
    cursor.close()
    connection.close()
    
    return jsonify({'message': 'Producto eliminado exitosamente'})

@app.route('/api/products/search', methods=['GET'])
def search_products():
    name = request.args.get('name')
    min_price = request.args.get('minPrice')
    max_price = request.args.get('maxPrice')
    min_stock = request.args.get('minStock')
    
    connection = get_db_connection()
    if not connection:
        return jsonify({'error': 'Error de conexión a la base de datos'}), 500
    
    cursor = connection.cursor(dictionary=True)
    
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if name:
        query += " AND name LIKE %s"
        params.append(f"%{name}%")
    if min_price:
        query += " AND price >= %s"
        params.append(float(min_price))
    if max_price:
        query += " AND price <= %s"
        params.append(float(max_price))
    if min_stock:
        query += " AND stock > %s"
        params.append(int(min_stock))
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    cursor.close()
    connection.close()
    
    for product in products:
        if 'price' in product and isinstance(product['price'], decimal.Decimal):
            product['price'] = float(product['price'])
    
    return jsonify(products)

if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', 8082))
    print(f"Backend 2 (Product Service) running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
