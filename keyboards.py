from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def user_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🍽 Меню"), KeyboardButton(text="🧾 Мои заказы")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )


def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛠 Админ-панель"), KeyboardButton(text="🍽 Меню")],
            [KeyboardButton(text="🪑 Активные столики"), KeyboardButton(text="📋 Все блюда")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Управление рестораном"
    )


def admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="admin_add_dish"),
            InlineKeyboardButton(text="✏️ Изменить блюдо", callback_data="admin_edit_dish")
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить блюдо", callback_data="admin_delete_dish"),
            InlineKeyboardButton(text="📋 Все блюда", callback_data="admin_all_dishes")
        ],
        [
            InlineKeyboardButton(text="📂 Добавить категорию", callback_data="admin_add_category"),
            InlineKeyboardButton(text="🪑 Активные столики", callback_data="admin_tables")
        ]
    ])


def categories_keyboard(rows, prefix="category"):
    buttons = [
        [InlineKeyboardButton(text=f"🍴 {row['name']}", callback_data=f"{prefix}:{row['id']}")]
        for row in rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dishes_keyboard(rows):
    buttons = [
        [InlineKeyboardButton(
            text=f"{row['name']} • {row['price']} сом.",
            callback_data=f"dish:{row['id']}"
        )]
        for row in rows
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ К категориям", callback_data="back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def dish_card_keyboard(dish_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Заказать", callback_data=f"order:{dish_id}")],
        [InlineKeyboardButton(text="⬅️ К меню", callback_data="back_categories")]
    ])


def select_dish_keyboard(rows, action):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{row['name']} • {row['price']} сом.",
            callback_data=f"{action}:{row['id']}"
        )]
        for row in rows
    ])


def edit_fields_keyboard(dish_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Название", callback_data=f"edit_field:{dish_id}:name"),
            InlineKeyboardButton(text="📄 Описание", callback_data=f"edit_field:{dish_id}:description")
        ],
        [
            InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_field:{dish_id}:price"),
            InlineKeyboardButton(text="📷 Фото", callback_data=f"edit_field:{dish_id}:photo_file_id")
        ],
        [
            InlineKeyboardButton(text="📂 Категория", callback_data=f"edit_field:{dish_id}:category_id")
        ]
    ])


def delete_confirm_keyboard(dish_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"delete_yes:{dish_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")
    ]])


def tables_keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🪑 Столик {row['table_number']} • {row['total']} сом.",
            callback_data=f"table:{row['table_number']}"
        )]
        for row in rows
    ])


def table_keyboard(table_number):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить столик", callback_data=f"finish:{table_number}")],
        [InlineKeyboardButton(text="⬅️ Активные столики", callback_data="admin_tables")]
    ])


def finish_confirm_keyboard(table_number):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, завершить", callback_data=f"finish_yes:{table_number}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"table:{table_number}")
    ]])
