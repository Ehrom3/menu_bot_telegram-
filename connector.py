import os
from decimal import Decimal
import asyncpg
from dotenv import load_dotenv

load_dotenv()
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))


async def get_connection():
    try:  
        return await asyncpg.connect(
            user="postgres",
            password=os.getenv("PASSWORD_DB"),
            database="menu_october",   
            host="localhost",
            port=5432
        )
        print("connect is okay")
    except Exception as er:
        print("Connection is error: ", er)
    


async def create_tables():
    connection = await get_connection()
    if connection is None:
        return
    try:
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                is_admin BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)

        await connection.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)

        await connection.execute("""
            CREATE TABLE IF NOT EXISTS dishes (
                id SERIAL PRIMARY KEY,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
                name TEXT NOT NULL,
                description TEXT,
                price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
                photo_file_id TEXT
            )
        """)

        await connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                dish_id INTEGER NOT NULL REFERENCES dishes(id) ON DELETE RESTRICT,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                table_number INTEGER NOT NULL CHECK (table_number > 0),
                customer_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP
            )
        """)

        print("Таблицы базы данных готовы.")
    except Exception as error:
        print(f"Ошибка при создании таблиц: {error}")
    finally:
        await connection.close()


async def register_user(telegram_id, username):
    connection = await get_connection()
    if connection is None:
        return
    try:
        admin = ADMIN_ID != 0 and telegram_id == ADMIN_ID
        await connection.execute("""
            INSERT INTO users (telegram_id, username, is_admin)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_id)
            DO UPDATE SET username=$2, is_admin=$3
        """, telegram_id, username, admin)
    except Exception as error:
        print(f"Ошибка register_user: {error}")
    finally:
        await connection.close()


async def is_admin(telegram_id):
    connection = await get_connection()
    if connection is None:
        return False
    try:
        result = await connection.fetchval(
            "SELECT is_admin FROM users WHERE telegram_id=$1", telegram_id
        )
        return bool(result)
    except Exception as error:
        print(f"Ошибка is_admin: {error}")
        return False
    finally:
        await connection.close()


async def get_admin_ids():
    connection = await get_connection()
    if connection is None:
        return []
    try:
        rows = await connection.fetch("SELECT telegram_id FROM users WHERE is_admin=TRUE")
        return [row["telegram_id"] for row in rows]
    except Exception as error:
        print(f"Ошибка get_admin_ids: {error}")
        return []
    finally:
        await connection.close()


async def get_categories():
    connection = await get_connection()
    if connection is None:
        return []
    try:
        return await connection.fetch("SELECT id, name FROM categories ORDER BY name")
    except Exception as error:
        print(f"Ошибка get_categories: {error}")
        return []
    finally:
        await connection.close()


async def add_category(name):
    connection = await get_connection()
    if connection is None:
        return None
    try:
        return await connection.fetchval(
            "INSERT INTO categories(name) VALUES($1) RETURNING id", name
        )
    finally:
        await connection.close()


async def get_dishes(category_id=None):
    connection = await get_connection()
    if connection is None:
        return []
    try:
        if category_id is None:
            return await connection.fetch("""
                SELECT d.*, c.name AS category
                FROM dishes d
                JOIN categories c ON c.id=d.category_id
                ORDER BY c.name, d.name
            """)
        return await connection.fetch("""
            SELECT d.*, c.name AS category
            FROM dishes d
            JOIN categories c ON c.id=d.category_id
            WHERE d.category_id=$1
            ORDER BY d.name
        """, category_id)
    finally:
        await connection.close()


async def get_dish(dish_id):
    connection = await get_connection()
    if connection is None:
        return None
    try:
        return await connection.fetchrow("""
            SELECT d.*, c.name AS category
            FROM dishes d
            JOIN categories c ON c.id=d.category_id
            WHERE d.id=$1
        """, dish_id)
    finally:
        await connection.close()


async def add_dish(category_id, name, description, price, photo_file_id):
    connection = await get_connection()
    if connection is None:
        return None
    try:
        return await connection.fetchval("""
            INSERT INTO dishes(category_id, name, description, price, photo_file_id)
            VALUES($1, $2, $3, $4, $5)
            RETURNING id
        """, category_id, name, description, Decimal(str(price)), photo_file_id)
    finally:
        await connection.close()


async def update_dish(dish_id, field, value):
    queries = {
        "name": "UPDATE dishes SET name=$1 WHERE id=$2",
        "description": "UPDATE dishes SET description=$1 WHERE id=$2",
        "price": "UPDATE dishes SET price=$1 WHERE id=$2",
        "photo_file_id": "UPDATE dishes SET photo_file_id=$1 WHERE id=$2",
        "category_id": "UPDATE dishes SET category_id=$1 WHERE id=$2"
    }
    query = queries.get(field)
    if query is None:
        raise ValueError("Недопустимое поле")

    connection = await get_connection()
    if connection is None:
        return
    try:
        await connection.execute(query, value, dish_id)
    finally:
        await connection.close()


async def delete_dish(dish_id):
    connection = await get_connection()
    if connection is None:
        return
    try:
        await connection.execute("DELETE FROM dishes WHERE id=$1", dish_id)
    finally:
        await connection.close()


async def create_order(telegram_id, dish_id, quantity, table_number, customer_name):
    connection = await get_connection()
    if connection is None:
        return None
    try:
        return await connection.fetchval("""
            INSERT INTO orders(telegram_id, dish_id, quantity, table_number, customer_name)
            VALUES($1, $2, $3, $4, $5)
            RETURNING id
        """, telegram_id, dish_id, quantity, table_number, customer_name)
    finally:
        await connection.close()


async def get_user_orders(telegram_id):
    connection = await get_connection()
    if connection is None:
        return []
    try:
        return await connection.fetch("""
            SELECT o.*, d.name, d.price,
                   (o.quantity*d.price)::NUMERIC(12,2) AS subtotal
            FROM orders o
            JOIN dishes d ON d.id=o.dish_id
            WHERE o.telegram_id=$1 AND o.status='active'
            ORDER BY o.created_at
        """, telegram_id)
    finally:
        await connection.close()


async def get_active_tables():
    connection = await get_connection()
    if connection is None:
        return []
    try:
        return await connection.fetch("""
            SELECT o.table_number,
                   SUM(o.quantity*d.price)::NUMERIC(12,2) AS total
            FROM orders o
            JOIN dishes d ON d.id=o.dish_id
            WHERE o.status='active'
            GROUP BY o.table_number
            ORDER BY o.table_number
        """)
    finally:
        await connection.close()


async def get_table_orders(table_number):
    connection = await get_connection()
    if connection is None:
        return []
    try:
        return await connection.fetch("""
            SELECT o.*, d.name, d.price,
                   (o.quantity*d.price)::NUMERIC(12,2) AS subtotal
            FROM orders o
            JOIN dishes d ON d.id=o.dish_id
            WHERE o.table_number=$1 AND o.status='active'
            ORDER BY o.created_at, o.id
        """, table_number)
    finally:
        await connection.close()


async def finish_table(table_number):
    connection = await get_connection()
    if connection is None:
        return
    try:
        await connection.execute("""
            UPDATE orders
            SET status='completed', completed_at=NOW()
            WHERE table_number=$1 AND status='active'
        """, table_number)
    finally:
        await connection.close()
