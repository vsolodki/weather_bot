import os
import requests
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Application
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

user_chats = {}

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!", 200

def get_weather(city='Prague'):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        temperature = data['main']['temp']
        weather_description = data['weather'][0]['description']

        if temperature < 10:
            clothing_recommendation = "Теплая одежда, шапка и перчатки."
        elif 10 <= temperature < 20:
            clothing_recommendation = "Легкая куртка или свитер."
        else:
            clothing_recommendation = "Легкая одежда, шорты и футболка."

        message = (f"Погода в {city}:\nТемпература: {temperature}°C\n"
                   f"{weather_description.capitalize()}\nРекомендуемая одежда: {clothing_recommendation}")
        return message
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к OpenWeather: {e}")
        return "Не удалось получить данные о погоде."

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.message.chat_id
    user_chats[user.id] = chat_id
    logger.info(f"Пользователь {user.first_name} начал взаимодействие с ботом.")
    
    await update.message.reply_text(f"Привет, {user.first_name}! Я твой бот для прогноза погоды. "
                                    "Ты можешь получать ежедневные уведомления о погоде.")

    await send_weather_update(chat_id, context)

async def weather(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    await send_weather_update(chat_id, context)

async def send_weather_update(chat_id, context: CallbackContext):
    message = get_weather()
    try:
        await context.bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Сообщение с погодой отправлено пользователю с chat_id: {chat_id}.")
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")

async def daily_weather_update(context: CallbackContext):
    for user_id, chat_id in user_chats.items():
        await send_weather_update(chat_id, context)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("weather", weather))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_weather_update, 'cron', hour=8, minute=0, args=[application])
    scheduler.start()

    # Start the Flask app
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)), debug=False)

if __name__ == '__main__':
    main()
