import asyncio
import logging
from aiogram import Bot, Dispatcher
from bot.config import BOT_TOKEN
from bot.handlers import start, appointment, my_appointments
from bot.handlers.doctor import router as doctor_router


    

async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(doctor_router)
    dp.include_router(start.router)
    dp.include_router(appointment.router)
    dp.include_router(my_appointments.router)

    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())