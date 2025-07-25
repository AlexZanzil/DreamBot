import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from bot.handlers.common import register_common_handlers
from bot.handlers.lunch import register_lunch_handlers
from bot.services.scheduler_instance import init_scheduler, LunchScheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функция запуска бота
async def main():
    logging.info("Запуск бота...")

    # Инициализация и запуск планировщика
    scheduler = init_scheduler(bot)
    scheduler.start()
    logging.info("Планировщик запущен")

    # Инициализация и запуск планировщика обедов
    lunch_scheduler = LunchScheduler(bot)
    asyncio.create_task(lunch_scheduler.start())
    logging.info("Планировщик обедов запущен")

    # Регистрация всех обработчиков
    register_common_handlers(dp)
    register_lunch_handlers(dp)
    logging.info("Все обработчики зарегистрированы")

    try:
        # Запуск бота
        logging.info("Бот готов к работе")
        await dp.start_polling(bot)
    finally:
        # Остановка планировщика при любом завершении
        await lunch_scheduler.stop()
        # Открепляем и удаляем сообщение при остановке бота
        await lunch_scheduler.cleanup_on_shutdown()
        logging.info("Бот очищен")
        try:
            scheduler.shutdown(wait=False)
            logging.info("Планировщик остановлен")
        except:
            pass

        # Закрытие сессии бота
        try:
            await bot.session.close()
            logging.info("Сессия бота закрыта")
        except:
            pass

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")