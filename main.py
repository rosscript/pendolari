from setup import dp
from handlers import general
from aiogram.utils import executor
from setup import on_startup

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)

