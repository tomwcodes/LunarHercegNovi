import os
import logging
from typing import Optional
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv  # type: ignore
from telegram import __version__ as TG_VER, Update  # type: ignore
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackContext,
    filters
)  # type: ignore

try:
    from telegram import __version_info__  # type: ignore
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"20.x version of this example, visit https://docs.python-telegram-bot.org/en/v20.7/examples.html"
    )

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if os.getenv('ENVIRONMENT') != 'production' else logging.WARNING
)
logger = logging.getLogger(__name__)

load_dotenv()

HERCEG_NOVI_LAT = 42.4531
HERCEG_NOVI_LON = 18.5375

async def get_weather_and_moon_data(city: Optional[str] = None) -> tuple:
    """
    Get current weather and moon data from Weatherbit.
    Returns: tuple(min_temp, max_temp, pressure, weather_description, moonrise, moonset, moon_phase, moon_illumination)
    """
    try:
        api_key = os.getenv('WEATHERBIT_API_KEY')
        if not api_key:
            logger.error("Weatherbit API key not found in environment variables")
            return None, None, None, None, None, None, None, None

        if city:
            url = f"https://api.weatherbit.io/v2.0/forecast/daily?city={city}&key={api_key}&days=1"
        else:
            url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={HERCEG_NOVI_LAT}&lon={HERCEG_NOVI_LON}&key={api_key}&days=1"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and len(data['data']) > 0:
                today_data = data['data'][0]
                min_temp = today_data.get('min_temp')
                max_temp = today_data.get('max_temp')
                pressure = today_data.get('pres')
                weather_description = today_data.get('weather', {}).get('description')
                moonrise = today_data.get('moonrise_ts')
                moonset = today_data.get('moonset_ts')
                moon_phase = today_data.get('moon_phase')
                moon_illumination = today_data.get('moon_phase_lunation')

                return min_temp, max_temp, pressure, weather_description, moonrise, moonset, moon_phase, moon_illumination
            else:
                logger.error("Missing data in API response")
                return None, None, None, None, None, None, None, None

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching data: {e}")
        return None, None, None, None, None, None, None, None

async def hi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /hi command."""
    try:
        min_temp, max_temp, pressure, weather_description, moonrise, moonset, moon_phase, moon_illumination = await get_weather_and_moon_data()
        current_date = datetime.now().strftime('%A %d/%m')
        
        if all(v is not None for v in [min_temp, max_temp, pressure, weather_description]):
            weather_info = (
                f"🌡 Weather: {weather_description}\n"
                f"❄️ Min Temp: {min_temp}°C\n"
                f"☀️ Max Temp: {max_temp}°C\n"
                f"🌬 Pressure: {pressure} hPa"
            )
        else:
            weather_info = "Weather data currently unavailable"
        
        if all(v is not None for v in [moonrise, moonset, moon_phase, moon_illumination]):
            moon_info = (
                f"🌙 Moonrise: {datetime.utcfromtimestamp(moonrise).strftime('%H:%M')} UTC\n"
                f"🌘 Moonset: {datetime.utcfromtimestamp(moonset).strftime('%H:%M')} UTC\n"
                f"🌖 Moon Phase: {moon_phase}\n"
                f"💡 Moon Illumination: {round(moon_illumination * 100, 1)}%"
            )
        else:
            moon_info = "Moon data currently unavailable"

        message = (
            f"🌍 Herceg Novi, {current_date}:\n"
            f"{weather_info}\n"
            f"{moon_info}"
        )

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in hi_command: {str(e)}")
        await update.message.reply_text("Sorry, an error occurred while processing your request.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text("Hello! 👋 Use /hi to get weather and moon data.")

def main() -> None:
    """Start the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("hi", hi_command))
    application.run_polling()

if __name__ == '__main__':
    main()
