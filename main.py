import os
import logging
from typing import Optional
import ephem  # type: ignore
from datetime import datetime, timedelta
from dotenv import load_dotenv  # type: ignore
import httpx
from telegram import __version__ as TG_VER, Update  # type: ignore
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if os.getenv('ENVIRONMENT') != 'production' else logging.WARNING
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Default coordinates for Herceg Novi
HERCEG_NOVI_LAT = 42.4531
HERCEG_NOVI_LON = 18.5375

async def get_weather(city: Optional[str] = None) -> tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[str],
    Optional[float],
    Optional[float]
]:
    """
    Get current weather forecast from Weatherbit.
    If a city is provided, it queries by city name; otherwise, it uses default coordinates.
    Returns a tuple:
      (min_temp, max_temp, pressure, weather_description, city_lat, city_lon)
    or (None, None, None, None, None, None) if an error occurs.
    """
    try:
        api_key = os.getenv('WEATHERBIT_API_KEY')
        if not api_key:
            logger.error("Weatherbit API key not found in environment variables")
            return None, None, None, None, None, None

        if city:
            url = f"https://api.weatherbit.io/v2.0/forecast/daily?city={city}&key={api_key}&days=1"
        else:
            url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={HERCEG_NOVI_LAT}&lon={HERCEG_NOVI_LON}&key={api_key}&days=1"

        if os.getenv('ENVIRONMENT') != 'production':
            key_info = url.split('key=')[0] + "key=<HIDDEN>"
            if city:
                logger.info(f"Making request to Weatherbit API for city '{city}': {key_info}")
            else:
                logger.info(f"Making request to Weatherbit API: {key_info}")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)

            if response.status_code == 403:
                logger.error("Invalid or expired API key. Please check your Weatherbit API key.")
                return None, None, None, None, None, None
            elif response.status_code == 429:
                logger.error("Too many requests. API rate limit exceeded.")
                return None, None, None, None, None, None

            response.raise_for_status()
            data = response.json()

            if os.getenv('ENVIRONMENT') != 'production':
                safe_data = {k: v for k, v in data.items() if k != 'data'}
                logger.info(f"API Response structure: {safe_data}")

            if 'data' in data and len(data['data']) > 0:
                today_data = data['data'][0]
                min_temp = round(float(today_data['min_temp']), 1) if 'min_temp' in today_data else None
                max_temp = round(float(today_data['max_temp']), 1) if 'max_temp' in today_data else None
                pressure = round(float(today_data['pres'])) if 'pres' in today_data else None
                weather_description = today_data.get('weather', {}).get('description')

                # Extract the city coordinates from the top-level response (if available)
                city_lat = data.get('lat')
                city_lon = data.get('lon')

                if os.getenv('ENVIRONMENT') != 'production':
                    logger.info(f"Weather data: Min {min_temp}°C, Max {max_temp}°C, Pressure {pressure} hPa")
                    logger.info(f"Weather description: {weather_description}")
                    logger.info(f"Coordinates: lat={city_lat}, lon={city_lon}")

                return min_temp, max_temp, pressure, weather_description, city_lat, city_lon
            else:
                logger.error("Missing weather data in API response")
                return None, None, None, None, None, None

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching weather data: {e}")
        return None, None, None, None, None, None
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing weather data: {e}")
        return None, None, None, None, None, None
    except Exception as e:
        logger.error(f"Unexpected error fetching weather data: {e}")
        return None, None, None, None, None, None

def get_sun_times(lat: float, lon: float, custom_date: Optional[datetime] = None) -> tuple:
    """
    Calculate sunrise and sunset times for a given latitude and longitude.
    Returns a tuple: (sunrise_time, sunset_time)
    """
    try:
        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lon)
        observer.elevation = 10  # assuming an elevation of 10m; adjust if needed
        observer.pressure = 0    # disable refraction calculation
        observer.horizon = '-0:34'
        now = custom_date if custom_date else datetime.utcnow()
        observer.date = ephem.Date(now)

        if os.getenv('ENVIRONMENT') != 'production':
            logger.info(f"Sun Times Calculation: lat={observer.lat}, lon={observer.lon}, elevation={observer.elevation}, date={now}")

        sun = ephem.Sun()
        sun.compute(observer)
        try:
            next_rising = observer.next_rising(sun)
            next_setting = observer.next_setting(sun)
            if os.getenv('ENVIRONMENT') != 'production':
                logger.info(f"Raw next rising: {next_rising}, Raw next setting: {next_setting}")
            sunrise_local = ephem.Date(next_rising).datetime() + timedelta(hours=1)
            sunset_local = ephem.Date(next_setting).datetime() + timedelta(hours=1)
        except ephem.CircumpolarError:
            logger.error("Sun is circumpolar at this location and date")
            return "No sunrise", "No sunset"

        sunrise_str = sunrise_local.strftime('%H:%M')
        sunset_str = sunset_local.strftime('%H:%M')
        if os.getenv('ENVIRONMENT') != 'production':
            logger.info(f"Formatted sunrise: {sunrise_str}, sunset: {sunset_str}")

        return sunrise_str, sunset_str

    except Exception as e:
        logger.error(f"Error calculating sun times: {str(e)}")
        return "Unknown", "Unknown"

async def hi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /hi command for the default location (Herceg Novi)."""
    try:
        logger.info("Received /hi command, calculating moon phase and weather...")
        # Get moon phase for default location
        phase_name, emoji = get_moon_phase()
        logger.info(f"Calculated moon phase: {phase_name} {emoji}")
        # Use default coordinates for Herceg Novi
        sunrise_time, sunset_time = get_sun_times(HERCEG_NOVI_LAT, HERCEG_NOVI_LON)
        # Get weather data for Herceg Novi
        min_temp, max_temp, pressure, weather_description, _, _ = await get_weather()

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

        message = (
            f"🌍 Herceg Novi, {current_date}:\n"
            f"🌅 Sunrise: {sunrise_time}\n"
            f"{weather_info}\n"
            f"🌇 Sunset: {sunset_time}\n"
            f"{emoji} Moon Phase: {phase_name}"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in hi_command: {e}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. Please try again later."
        )

async def city_forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle commands that are not explicitly registered.
    This function assumes the command (e.g. /london) represents a city name.
    It retrieves weather data, extracts the city coordinates,
    calculates sunrise and sunset times for that city, and returns the forecast.
    """
    try:
        # Extract the command text without the leading slash.
        command_text = update.message.text.strip()
        if not command_text.startswith('/'):
            return

        city_name = command_text[1:].split()[0]  # e.g., "london" from "/london"
        if not city_name:
            await update.message.reply_text("Please provide a valid city name.")
            return

        # Get weather data and coordinates for the requested city.
        min_temp, max_temp, pressure, weather_description, city_lat, city_lon = await get_weather(city=city_name)
        if None in [min_temp, max_temp, pressure, weather_description]:
            forecast_message = f"Weather data for {city_name.title()} is currently unavailable."
        else:
            # Calculate sunrise and sunset times using the city's coordinates if available.
            if city_lat is not None and city_lon is not None:
                sunrise_time, sunset_time = get_sun_times(city_lat, city_lon)
                sun_info = f"🌅 Sunrise: {sunrise_time}\n🌇 Sunset: {sunset_time}\n"
            else:
                sun_info = ""

            forecast_message = (
                f"Forecast for {city_name.title()}:\n"
                f"🌡 Weather: {weather_description}\n"
                f"❄️ Min Temp: {min_temp}°C\n"
                f"☀️ Max Temp: {max_temp}°C\n"
                f"🌬 Pressure: {pressure} hPa\n"
                f"{sun_info}"
            )
        await update.message.reply_text(forecast_message)
    except Exception as e:
        logger.error(f"Error in city_forecast_command: {e}")
        await update.message.reply_text("Sorry, an error occurred while retrieving the forecast.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send updated welcome message."""
    try:
        logger.info("Received /start command, sending welcome message...")
        message = (
            "Hello! 👋\n\n"
            "Get weather data for Herceg Novi using /hi.\n\n"
            "Or request another city's forecast by typing a command in this format:\n"
            "e.g., /london, /moscow, /tokyo."
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. Please try again later."
        )

async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the Telegram bot."""
    error_message = f"Error: {context.error}"
    if update:
        error_message = f"Update {update} caused {error_message}"
    logger.error(error_message)
    try:
        if update is not None and update.message is not None:
            await update.message.reply_text("Sorry, something went wrong. Please try again later.")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

def main() -> None:
    """Start the bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.critical("No token found! Make sure to set TELEGRAM_BOT_TOKEN environment variable.")
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    try:
        application = Application.builder().token(token).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("hi", hi_command))
        # Any unregistered command (e.g., /london, /moscow) is handled here.
        application.add_handler(MessageHandler(filters.COMMAND, city_forecast_command))
        application.add_error_handler(error_handler)
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Error starting bot: {e}")
        raise

if __name__ == '__main__':
    main()
