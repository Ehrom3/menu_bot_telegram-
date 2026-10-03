from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    quantity = State()
    table_number = State()
    customer_name = State()


class AddCategoryState(StatesGroup):
    name = State()


class AddDishState(StatesGroup):
    category = State()
    name = State()
    description = State()
    price = State()
    photo = State()


class EditDishState(StatesGroup):
    value = State()
