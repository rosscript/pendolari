from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from database import create_tables, verify_and_update_subscriptions, set_premium_expiration_to_yesterday
import logging
import aiocron
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

api_token = os.getenv("API_TOKEN")
bot = Bot(token=api_token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

logging.basicConfig(level=logging.INFO)

# Schedula il job per la verifica degli abbonamenti
@aiocron.crontab('0 0 * * *')
async def scheduled_job(): # Ogni giorno alle 00:00
    await verify_and_update_subscriptions(bot) # Verifica gli abbonamenti

async def on_startup(_):
    await create_tables() # Crea le tabelle del database
    #await set_premium_expiration_to_yesterday() # Per testare la verifica degli abbonamenti
    await verify_and_update_subscriptions(bot) # Verifica gli abbonamenti all'avvio del bot
    scheduled_job.start()  # Avvia il job schedulato all'avvio del bot

if __name__ == '__main__':
    dp.loop.create_task(on_startup(None))  # Esegui on_startup
    dp.loop.run_forever()  # Esegui il loop di asyncio