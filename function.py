from decimal import Decimal, InvalidOperation
import html

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

import connector as db
from states import OrderState, AddCategoryState, AddDishState, EditDishState
from keyboards import (
    user_keyboard, admin_keyboard, admin_panel_keyboard,
    categories_keyboard, dishes_keyboard, dish_card_keyboard,
    select_dish_keyboard, edit_fields_keyboard, delete_confirm_keyboard,
    tables_keyboard, table_keyboard, finish_confirm_keyboard
)

router = Router()


async def role_keyboard(user_id):
    return admin_keyboard() if await db.is_admin(user_id) else user_keyboard()


async def admin_guard(event):
    if await db.is_admin(event.from_user.id):
        return True

    if isinstance(event, CallbackQuery):
        await event.answer("⛔ У вас нет доступа к админ-панели.", show_alert=True)
    else:
        await event.answer("⛔ У вас нет доступа к админ-панели.")
    return False


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await db.register_user(message.from_user.id, message.from_user.username)

    print("-" * 45)
    print(f"Пользователь: {message.from_user.full_name}")
    print(f"Username: @{message.from_user.username}" if message.from_user.username else "Username: нет")
    print(f"Telegram ID: {message.from_user.id}")
    print("Скопируйте этот ID в ADMIN_ID файла .env, если хотите сделать пользователя администратором.")
    print("-" * 45)

    if await db.is_admin(message.from_user.id):
        await message.answer(
            "👨‍💼 <b>АДМИНИСТРАТОР</b>\n\n"
            "Добро пожаловать в систему управления рестораном.\n"
            "Используйте кнопки снизу или откройте админ-панель.",
            reply_markup=admin_keyboard()
        )
    else:
        await message.answer(
            "👋 <b>Добро пожаловать в ресторан!</b>\n\n"
            "Здесь вы можете посмотреть меню и оформить заказ прямо со своего столика.",
            reply_markup=user_keyboard()
        )


# -------------------- USER --------------------

async def show_categories(event):
    rows = await db.get_categories()

    if not rows:
        text = "🍽 Меню пока пустое."
        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    text = "🍽 <b>МЕНЮ РЕСТОРАНА</b>\n\nВыберите категорию:"

    if isinstance(event, CallbackQuery):
        await event.message.answer(text, reply_markup=categories_keyboard(rows))
        await event.answer()
    else:
        await event.answer(text, reply_markup=categories_keyboard(rows))


@router.message(F.text == "🍽 Меню")
async def menu(message: Message):
    await show_categories(message)


@router.callback_query(F.data == "back_categories")
async def back_categories(call: CallbackQuery):
    await show_categories(call)


@router.callback_query(F.data.startswith("category:"))
async def open_category(call: CallbackQuery):
    category_id = int(call.data.split(":")[1])
    rows = await db.get_dishes(category_id)

    if not rows:
        await call.answer("В этой категории пока нет блюд.", show_alert=True)
        return

    await call.message.answer(
        "🍴 <b>Выберите блюдо:</b>",
        reply_markup=dishes_keyboard(rows)
    )
    await call.answer()


@router.callback_query(F.data.startswith("dish:"))
async def open_dish(call: CallbackQuery):
    dish_id = int(call.data.split(":")[1])
    row = await db.get_dish(dish_id)

    if not row:
        await call.answer("Блюдо не найдено.", show_alert=True)
        return

    text = (
        f"🍽 <b>{html.escape(row['name'])}</b>\n"
        f"📂 {html.escape(row['category'])}\n"
        f"💰 <b>{row['price']} сом.</b>\n\n"
        f"{html.escape(row['description'] or 'Без описания')}"
    )

    if row["photo_file_id"]:
        await call.message.answer_photo(
            row["photo_file_id"],
            caption=text,
            reply_markup=dish_card_keyboard(row["id"])
        )
    else:
        await call.message.answer(
            text,
            reply_markup=dish_card_keyboard(row["id"])
        )

    await call.answer()


@router.callback_query(F.data.startswith("order:"))
async def begin_order(call: CallbackQuery, state: FSMContext):
    dish_id = int(call.data.split(":")[1])
    row = await db.get_dish(dish_id)

    if not row:
        await call.answer("Блюдо не найдено.", show_alert=True)
        return

    await state.clear()
    await state.update_data(
        dish_id=dish_id,
        dish_name=row["name"],
        price=str(row["price"])
    )
    await state.set_state(OrderState.quantity)

    await call.message.answer(
        f"🛒 <b>{html.escape(row['name'])}</b>\n\n"
        "Введите количество:",
        reply_markup=ReplyKeyboardRemove()
    )
    await call.answer()


@router.message(OrderState.quantity)
async def order_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity < 1 or quantity > 100:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("⚠️ Введите целое число от 1 до 100.")
        return

    await state.update_data(quantity=quantity)
    await state.set_state(OrderState.table_number)
    await message.answer("🪑 Введите номер вашего столика:")


@router.message(OrderState.table_number)
async def order_table(message: Message, state: FSMContext):
    try:
        table_number = int(message.text)
        if table_number < 1 or table_number > 1000:
            raise ValueError
    except (TypeError, ValueError):
        await message.answer("⚠️ Введите корректный номер столика.")
        return

    await state.update_data(table_number=table_number)
    await state.set_state(OrderState.customer_name)
    await message.answer("👤 Введите ваше имя:")


@router.message(OrderState.customer_name)
async def order_name(message: Message, state: FSMContext, bot: Bot):
    customer_name = (message.text or "").strip()

    if len(customer_name) < 2:
        await message.answer("⚠️ Введите корректное имя.")
        return

    data = await state.get_data()

    order_id = await db.create_order(
        message.from_user.id,
        data["dish_id"],
        data["quantity"],
        data["table_number"],
        customer_name
    )

    total = Decimal(data["price"]) * data["quantity"]

    await state.clear()

    await message.answer(
        f"✅ <b>ЗАКАЗ №{order_id} ПРИНЯТ</b>\n\n"
        f"🍽 {html.escape(data['dish_name'])} × {data['quantity']}\n"
        f"🪑 Столик: <b>{data['table_number']}</b>\n"
        f"💰 Сумма: <b>{total:.2f} сом.</b>\n\n"
        "Вы можете добавить другие блюда — они попадут в общий счёт этого столика.",
        reply_markup=await role_keyboard(message.from_user.id)
    )

    # Администратор сразу получает уведомление о новом заказе.
    for admin_id in await db.get_admin_ids():
        if admin_id == message.from_user.id:
            continue
        try:
            await bot.send_message(
                admin_id,
                f"🔔 <b>НОВЫЙ ЗАКАЗ</b>\n\n"
                f"🪑 Столик: <b>{data['table_number']}</b>\n"
                f"👤 {html.escape(customer_name)}\n"
                f"🍽 {html.escape(data['dish_name'])} × {data['quantity']}\n"
                f"💰 {total:.2f} сом."
            )
        except Exception:
            pass


@router.message(F.text == "🧾 Мои заказы")
async def my_orders(message: Message):
    rows = await db.get_user_orders(message.from_user.id)

    if not rows:
        await message.answer("🧾 У вас нет активных заказов.")
        return

    total = sum((row["subtotal"] for row in rows), Decimal("0"))

    lines = ["🧾 <b>ВАШ ТЕКУЩИЙ ЗАКАЗ</b>", ""]

    for row in rows:
        lines.append(
            f"• {html.escape(row['name'])} × {row['quantity']} "
            f"= {row['subtotal']} сом."
        )

    lines.extend(["", f"💰 <b>Итого: {total:.2f} сом.</b>"])
    await message.answer("\n".join(lines))


# -------------------- ADMIN --------------------

@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: Message):
    if not await admin_guard(message):
        return

    await message.answer(
        "🛠 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "Выберите нужное действие:",
        reply_markup=admin_panel_keyboard()
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(call: CallbackQuery):
    if not await admin_guard(call):
        return

    await call.message.answer(
        "🛠 <b>АДМИН-ПАНЕЛЬ</b>",
        reply_markup=admin_panel_keyboard()
    )
    await call.answer()


async def send_all_dishes(message: Message):
    rows = await db.get_dishes()

    if not rows:
        await message.answer("📋 Блюд пока нет.")
        return

    lines = ["📋 <b>ВСЕ БЛЮДА</b>", ""]

    for row in rows:
        lines.append(
            f"#{row['id']} • {html.escape(row['category'])} → "
            f"<b>{html.escape(row['name'])}</b> — {row['price']} сом."
        )

    await message.answer("\n".join(lines))


@router.message(F.text == "📋 Все блюда")
async def all_dishes_message(message: Message):
    if await admin_guard(message):
        await send_all_dishes(message)


@router.callback_query(F.data == "admin_all_dishes")
async def all_dishes_callback(call: CallbackQuery):
    if not await admin_guard(call):
        return

    await send_all_dishes(call.message)
    await call.answer()


# ADD CATEGORY

@router.callback_query(F.data == "admin_add_category")
async def add_category_start(call: CallbackQuery, state: FSMContext):
    if not await admin_guard(call):
        return

    await state.clear()
    await state.set_state(AddCategoryState.name)
    await call.message.answer("📂 Введите название новой категории:")
    await call.answer()


@router.message(AddCategoryState.name)
async def add_category_name(message: Message, state: FSMContext):
    if not await admin_guard(message):
        await state.clear()
        return

    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer("⚠️ Название слишком короткое.")
        return

    try:
        await db.add_category(name)
    except Exception:
        await message.answer("⚠️ Такая категория уже существует.")
        return

    await state.clear()
    await message.answer(
        f"✅ Категория <b>{html.escape(name)}</b> добавлена.",
        reply_markup=admin_keyboard()
    )


# ADD DISH

@router.callback_query(F.data == "admin_add_dish")
async def add_dish_start(call: CallbackQuery, state: FSMContext):
    if not await admin_guard(call):
        return

    rows = await db.get_categories()

    if not rows:
        await call.answer(
            "Сначала создайте хотя бы одну категорию.",
            show_alert=True
        )
        return

    await state.clear()
    await state.set_state(AddDishState.category)

    await call.message.answer(
        "📂 Выберите категорию блюда:",
        reply_markup=categories_keyboard(rows, "add_dish_category")
    )
    await call.answer()


@router.callback_query(
    AddDishState.category,
    F.data.startswith("add_dish_category:")
)
async def add_dish_category(call: CallbackQuery, state: FSMContext):
    category_id = int(call.data.split(":")[1])

    await state.update_data(category_id=category_id)
    await state.set_state(AddDishState.name)

    await call.message.answer("🍽 Введите название блюда:")
    await call.answer()


@router.message(AddDishState.name)
async def add_dish_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer("⚠️ Введите нормальное название.")
        return

    await state.update_data(name=name)
    await state.set_state(AddDishState.description)
    await message.answer("📝 Введите описание блюда:")


@router.message(AddDishState.description)
async def add_dish_description(message: Message, state: FSMContext):
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(AddDishState.price)
    await message.answer("💰 Введите цену, например: <b>45.50</b>")


@router.message(AddDishState.price)
async def add_dish_price(message: Message, state: FSMContext):
    try:
        price = Decimal((message.text or "").replace(",", "."))
        if not price.is_finite() or price < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer("⚠️ Введите корректную цену.")
        return

    await state.update_data(price=str(price))
    await state.set_state(AddDishState.photo)
    await message.answer("📷 Теперь отправьте фотографию блюда:")


@router.message(AddDishState.photo, F.photo)
async def add_dish_photo(message: Message, state: FSMContext):
    data = await state.get_data()

    await db.add_dish(
        data["category_id"],
        data["name"],
        data["description"],
        data["price"],
        message.photo[-1].file_id
    )

    await state.clear()

    await message.answer(
        f"✅ Блюдо <b>{html.escape(data['name'])}</b> успешно добавлено.",
        reply_markup=admin_keyboard()
    )


@router.message(AddDishState.photo)
async def add_dish_photo_wrong(message: Message):
    await message.answer("⚠️ Отправьте именно фотографию блюда.")


# EDIT DISH

@router.callback_query(F.data == "admin_edit_dish")
async def edit_dish_start(call: CallbackQuery):
    if not await admin_guard(call):
        return

    rows = await db.get_dishes()

    if not rows:
        await call.answer("Блюд пока нет.", show_alert=True)
        return

    await call.message.answer(
        "✏️ <b>Выберите блюдо для изменения:</b>",
        reply_markup=select_dish_keyboard(rows, "edit_dish")
    )
    await call.answer()


@router.callback_query(F.data.startswith("edit_dish:"))
async def edit_dish_select(call: CallbackQuery):
    if not await admin_guard(call):
        return

    dish_id = int(call.data.split(":")[1])
    row = await db.get_dish(dish_id)

    await call.message.answer(
        f"✏️ Блюдо: <b>{html.escape(row['name'])}</b>\n"
        "Что хотите изменить?",
        reply_markup=edit_fields_keyboard(dish_id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("edit_field:"))
async def edit_field(call: CallbackQuery, state: FSMContext):
    if not await admin_guard(call):
        return

    _, dish_id, field = call.data.split(":")

    if field == "category_id":
        rows = await db.get_categories()

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=row["name"],
                callback_data=f"edit_category:{dish_id}:{row['id']}"
            )]
            for row in rows
        ])

        await call.message.answer(
            "📂 Выберите новую категорию:",
            reply_markup=keyboard
        )
        await call.answer()
        return

    await state.clear()
    await state.update_data(dish_id=int(dish_id), field=field)
    await state.set_state(EditDishState.value)

    if field == "photo_file_id":
        await call.message.answer("📷 Отправьте новое фото:")
    else:
        await call.message.answer("✏️ Введите новое значение:")

    await call.answer()


@router.callback_query(F.data.startswith("edit_category:"))
async def edit_category(call: CallbackQuery):
    if not await admin_guard(call):
        return

    _, dish_id, category_id = call.data.split(":")

    await db.update_dish(
        int(dish_id),
        "category_id",
        int(category_id)
    )

    await call.message.answer("✅ Категория блюда изменена.")
    await call.answer()


@router.message(EditDishState.value)
async def edit_value(message: Message, state: FSMContext):
    if not await admin_guard(message):
        await state.clear()
        return

    data = await state.get_data()
    field = data["field"]

    if field == "photo_file_id":
        if not message.photo:
            await message.answer("⚠️ Отправьте фотографию.")
            return
        value = message.photo[-1].file_id

    elif field == "price":
        try:
            value = Decimal((message.text or "").replace(",", "."))
            if not value.is_finite() or value < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            await message.answer("⚠️ Введите корректную цену.")
            return

    else:
        value = (message.text or "").strip()
        if not value:
            await message.answer("⚠️ Значение не может быть пустым.")
            return

    await db.update_dish(data["dish_id"], field, value)
    await state.clear()

    await message.answer(
        "✅ Блюдо успешно изменено.",
        reply_markup=admin_keyboard()
    )


# DELETE DISH

@router.callback_query(F.data == "admin_delete_dish")
async def delete_dish_start(call: CallbackQuery):
    if not await admin_guard(call):
        return

    rows = await db.get_dishes()

    if not rows:
        await call.answer("Блюд пока нет.", show_alert=True)
        return

    await call.message.answer(
        "🗑 <b>Выберите блюдо для удаления:</b>",
        reply_markup=select_dish_keyboard(rows, "delete_dish")
    )
    await call.answer()


@router.callback_query(F.data.startswith("delete_dish:"))
async def delete_dish_select(call: CallbackQuery):
    if not await admin_guard(call):
        return

    dish_id = int(call.data.split(":")[1])
    row = await db.get_dish(dish_id)

    await call.message.answer(
        f"⚠️ Удалить блюдо <b>{html.escape(row['name'])}</b>?",
        reply_markup=delete_confirm_keyboard(dish_id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("delete_yes:"))
async def delete_dish_yes(call: CallbackQuery):
    if not await admin_guard(call):
        return

    dish_id = int(call.data.split(":")[1])

    try:
        await db.delete_dish(dish_id)
        await call.message.answer("✅ Блюдо удалено.")
    except Exception:
        await call.message.answer(
            "⚠️ Это блюдо уже используется в истории заказов, "
            "поэтому удалить его нельзя."
        )

    await call.answer()


# TABLES

async def show_tables(event):
    rows = await db.get_active_tables()

    if not rows:
        text = "🪑 Сейчас нет активных столиков."

        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    text = (
        "🪑 <b>АКТИВНЫЕ СТОЛИКИ</b>\n\n"
        "Выберите столик, чтобы увидеть полный заказ:"
    )

    if isinstance(event, CallbackQuery):
        await event.message.answer(
            text,
            reply_markup=tables_keyboard(rows)
        )
        await event.answer()
    else:
        await event.answer(
            text,
            reply_markup=tables_keyboard(rows)
        )


@router.message(F.text == "🪑 Активные столики")
async def active_tables_message(message: Message):
    if await admin_guard(message):
        await show_tables(message)


@router.callback_query(F.data == "admin_tables")
async def active_tables_callback(call: CallbackQuery):
    if await admin_guard(call):
        await show_tables(call)


@router.callback_query(F.data.startswith("table:"))
async def open_table(call: CallbackQuery):
    if not await admin_guard(call):
        return

    table_number = int(call.data.split(":")[1])
    rows = await db.get_table_orders(table_number)

    if not rows:
        await call.answer(
            "Этот столик уже завершён.",
            show_alert=True
        )
        return

    total = sum((row["subtotal"] for row in rows), Decimal("0"))

    lines = [
        f"🪑 <b>СТОЛИК №{table_number}</b>",
        ""
    ]

    for row in rows:
        lines.append(
            f"• {html.escape(row['name'])} × {row['quantity']} "
            f"= {row['subtotal']} сом."
        )

    lines.extend([
        "",
        f"💰 <b>ОБЩИЙ СЧЁТ: {total:.2f} сом.</b>"
    ])

    await call.message.answer(
        "\n".join(lines),
        reply_markup=table_keyboard(table_number)
    )
    await call.answer()


@router.callback_query(F.data.startswith("finish:"))
async def finish_table_question(call: CallbackQuery):
    if not await admin_guard(call):
        return

    table_number = int(call.data.split(":")[1])
    rows = await db.get_table_orders(table_number)

    if not rows:
        await call.answer("Столик уже завершён.", show_alert=True)
        return

    total = sum((row["subtotal"] for row in rows), Decimal("0"))

    await call.message.answer(
        f"⚠️ Завершить обслуживание столика "
        f"<b>№{table_number}</b>?\n\n"
        f"💰 Итоговый счёт: <b>{total:.2f} сом.</b>",
        reply_markup=finish_confirm_keyboard(table_number)
    )
    await call.answer()


@router.callback_query(F.data.startswith("finish_yes:"))
async def finish_table_yes(call: CallbackQuery):
    if not await admin_guard(call):
        return

    table_number = int(call.data.split(":")[1])
    rows = await db.get_table_orders(table_number)

    if not rows:
        await call.answer("Столик уже завершён.", show_alert=True)
        return

    total = sum((row["subtotal"] for row in rows), Decimal("0"))

    await db.finish_table(table_number)

    await call.message.answer(
        f"✅ <b>СТОЛИК №{table_number} ЗАВЕРШЁН</b>\n\n"
        f"💰 Итоговая сумма: <b>{total:.2f} сом.</b>\n"
        "Столик снова свободен."
    )
    await call.answer("Столик завершён")


# HELP / FALLBACK

@router.message(F.text == "ℹ️ Помощь")
async def help_message(message: Message):
    if await db.is_admin(message.from_user.id):
        await message.answer(
            "ℹ️ <b>АДМИНИСТРАТОР</b>\n\n"
            "🛠 Админ-панель — управление меню.\n"
            "🪑 Активные столики — все текущие счета.\n"
            "📋 Все блюда — список меню.\n\n"
            "После ухода гостей откройте столик и нажмите "
            "«✅ Завершить столик»."
        )
    else:
        await message.answer(
            "ℹ️ <b>КАК СДЕЛАТЬ ЗАКАЗ</b>\n\n"
            "1. Нажмите «🍽 Меню».\n"
            "2. Выберите категорию.\n"
            "3. Выберите блюдо.\n"
            "4. Нажмите «🛒 Заказать».\n"
            "5. Укажите количество, столик и имя."
        )


@router.message()
async def fallback(message: Message):
    await message.answer(
        "Используйте кнопки меню 👇",
        reply_markup=await role_keyboard(message.from_user.id)
    )
