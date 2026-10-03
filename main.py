import os
import asyncio
import logging

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

import connector
from function import router

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден. Создайте файл .env и укажите BOT_TOKEN."
        )

    logging.basicConfig(level=logging.INFO)

    await connector.create_tables()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher()
    dp.include_router(router)

    try:
        print("Restaurant bot started...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
