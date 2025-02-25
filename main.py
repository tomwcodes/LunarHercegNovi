import os
import logging
from typing import Optional
import httpx
from datetime import datetime
from dotenv import load_dotenv  # type: ignore
from telegram import __version__ as TG_VER, Update  # type: ignore
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    filters
)  # type: ignore

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if os.getenv('ENVIRONMENT') != 'production' else logging.WARNING
)
logger = logging.getLogger(__name__)

load_dotenv()

HERCEG_NOVI_LAT = 42.4531
HERCEG_NOVI_LON = 18.5375

def get_moon_phase_name(moon_phase: float) -> str:
    """
    Convert moon phase numerical value to a text description.
    """
    if not 0 <= moon_phase <= 1:
        raise ValueError("Moon phase must be between 0 and 1.")

    phase_intervals = [
        (0, 0.125, "New Moon"),
        (0.125, 0.25, "Waxing Crescent"),
        (0.25, 0.375, "First Quarter"),
        (0.375, 0.5, "Waxing Gibbous"),
        (0.5, 0.625, "Full Moon"),
        (0.625, 0.75, "Waning Gibbous"),
        (0.75, 0.875, "Last Quarter"),
        (0.875, 1, "Waning Crescent"),
    ]

    for lower, upper, phase_name in phase_intervals:
        if lower <= moon_phase < upper:
            return phase_name

async def get_weather_and_moon_data(city: Optional[str] = None) -> tuple:
    """
    Get current weather and moon data from Weatherbit.
    Returns: tuple(min_temp, max_temp, pressure, weather_description, moonrise, moonset, moon_phase_text, moon_illumination, sunrise, sunset)
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

                moon_phase_text = get_moon_phase_name(moon_phase) if moon_phase is not None else "Unknown"

                sunrise = today_data.get('sunrise_ts')
                sunset = today_data.get('sunset_ts')

                return min_temp, max_temp, pressure, weather_description, moonrise, moonset, moon_phase_text, moon_illumination, sunrise, sunset
            else:
                logger.error("Missing data in API response")
                return None, None, None, None, None, None, None, None, None, None

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching data: {e}")
        return None, None, None, None, None, None, None, None, None, None

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle weather commands."""
    try:
        command = update.message.text[1:]  # Remove the '/' from command
        city = command.capitalize() if command not in ["hi", "start"] else None
        
        min_temp, max_temp, pressure, weather_description, moonrise, moonset, moon_phase_text, moon_illumination, sunrise, sunset = await get_weather_and_moon_data(city)
        current_date = datetime.now().strftime('%A %d/%m')
        location = city or "Herceg Novi"
        
        message = (
            f"🌍 {location}, {current_date}:\n"
            f"🌡 Weather: {weather_description}\n"
            f"❄️ Min Temp: {min_temp}°C\n"
            f"☀️ Max Temp: {max_temp}°C\n"
            f"🌬 Pressure: {pressure} hPa\n"
            f"🌖 Moon Phase: {moon_phase_text}\n"
            f"🌅 Sunrise: {datetime.fromtimestamp(sunrise).strftime('%H:%M')}\n"
            f"🌇 Sunset: {datetime.fromtimestamp(sunset).strftime('%H:%M')}"
        ) if all(v is not None for v in [min_temp, max_temp, pressure, weather_description, moon_phase_text, sunrise, sunset]) else "Weather data currently unavailable"

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in weather_command: {str(e)}")
        await update.message.reply_text("Sorry, an error occurred while processing your request.")

def main() -> None:
    """Start the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    application = Application.builder().token(token).build()
    
    # Add handlers for specific commands
    application.add_handler(CommandHandler("start", weather_command))
    application.add_handler(CommandHandler("hi", weather_command))
    
    # Add handler for any command (for city queries)
    application.add_handler(CommandHandler(filters.Command.ALL, weather_command))
    
    application.run_polling()

if __name__ == '__main__':
    main()
