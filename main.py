import os
import logging
from typing import Union, Optional
import ephem  # type: ignore
from datetime import datetime, timedelta
from dotenv import load_dotenv  # type: ignore
import httpx
from telegram import __version__ as TG_VER, Update  # type: ignore
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext  # type: ignore

try:
    from telegram import __version_info__  # type: ignore
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"20.x version of this example, visit https://docs.python-telegram-bot.org/en/v20.7/examples.html"
    )

# Configure logging with more detailed format for production
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

async def get_weather(city: Optional[str] = None) -> tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
    """
    Get current weather data from Weatherbit.
    If a city is provided, retrieve forecast using the city name.
    Otherwise, use default coordinates (Herceg Novi).
    Returns: tuple(min_temp, max_temp, pressure, weather_description)
             or (None, None, None, None) if error occurs.
    """
    try:
        api_key = os.getenv('WEATHERBIT_API_KEY')
        if not api_key:
            logger.error("Weatherbit API key not found in environment variables")
            return None, None, None, None

        # Build URL: if city is provided, use it; otherwise use lat/lon for Herceg Novi.
        if city:
            url = f"https://api.weatherbit.io/v2.0/forecast/daily?city={city}&key={api_key}&days=1"
        else:
            url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={HERCEG_NOVI_LAT}&lon={HERCEG_NOVI_LON}&key={api_key}&days=1"

        if os.getenv('ENVIRONMENT') != 'production':
            if city:
                logger.info(f"Making request to Weatherbit API for city '{city}' (without key): {url.split('key=')[0]}key=<HIDDEN>")
            else:
                logger.info(f"Making request to Weatherbit API (without key): {url.split('key=')[0]}key=<HIDDEN>")

        async with httpx.AsyncClient() as client:
            response = await client.get(url)

            # Check for specific error status codes
            if response.status_code == 403:
                logger.error("Invalid or expired API key. Please check your Weatherbit API key.")
                return None, None, None, None
            elif response.status_code == 429:
                logger.error("Too many requests. API rate limit exceeded.")
                return None, None, None, None

            response.raise_for_status()
            data = response.json()

            if os.getenv('ENVIRONMENT') != 'production':
                safe_data = {k: v for k, v in data.items() if k != 'data'}
                logger.info(f"API Response structure: {safe_data}")

            if 'data' in data and len(data['data']) > 0:
                today_data = data['data'][0]
                # Extract temperature and pressure details
                min_temp = round(float(today_data['min_temp']), 1) if 'min_temp' in today_data else None
                max_temp = round(float(today_data['max_temp']), 1) if 'max_temp' in today_data else None
                pressure = round(float(today_data['pres'])) if 'pres' in today_data else None

                if os.getenv('ENVIRONMENT') != 'production':
                    logger.info(f"Weather data retrieved: Min {min_temp}°C, Max {max_temp}°C, Pressure {pressure} hPa")
                
                # Extract weather description from the nested weather object
                weather_description = today_data.get('weather', {}).get('description')
                if os.getenv('ENVIRONMENT') != 'production':
                    logger.info(f"Weather description: {weather_description}")

                return min_temp, max_temp, pressure, weather_description
            else:
                logger.error("Missing weather data in API response")
                return None, None, None, None

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching weather data: {e}")
        return None, None, None, None
    except (ValueError, TypeError) as e:
        logger.error(f"Error processing weather data: {e}")
        return None, None, None, None
    except Exception as e:
        logger.error(f"Unexpected error fetching weather data: {e}")
        return None, None, None, None

def get_sun_times(custom_date: Optional[datetime] = None) -> tuple:
    """
    Calculate sunrise and sunset times for Herceg Novi.
    Args:
        custom_date: Optional datetime object for testing specific dates
    Returns: tuple(sunrise_time, sunset_time)
    """
    try:
        observer = ephem.Observer()
        observer.lat = str(HERCEG_NOVI_LAT)
        observer.lon = str(HERCEG_NOVI_LON)
        observer.elevation = 10
        observer.pressure = 0
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

def get_moon_phase(custom_date: Optional[datetime] = None) -> tuple:
    """
    Calculate the current moon phase for Herceg Novi.
    Args:
        custom_date: Optional datetime object for testing specific dates
    Returns: tuple(phase_name, emoji)
    """
    try:
        observer = ephem.Observer()
        observer.lat = str(HERCEG_NOVI_LAT)
        observer.lon = str(HERCEG_NOVI_LON)
        observer.elevation = 10

        moon = ephem.Moon()
        moon.compute(observer)
        current_date = ephem.Date(custom_date) if custom_date else ephem.Date(datetime.utcnow())
        previous_new = ephem.previous_new_moon(current_date)
        next_new = ephem.next_new_moon(current_date)
        moon_age = current_date - previous_new
        moon_cycle = next_new - previous_new
        phase_percent = (moon_age / moon_cycle) * 100

        if os.getenv('ENVIRONMENT') != 'production':
            logger.info(f"Moon Phase Calculation: current_date={ephem.Date(current_date).datetime()}, "
                        f"previous_new={ephem.Date(previous_new).datetime()}, next_new={ephem.Date(next_new).datetime()}, "
                        f"phase_percent={phase_percent}%")

        if phase_percent >= 97 or phase_percent <= 3:
            return "Full Moon", "🌕"
        elif phase_percent > 50 and phase_percent < 97:
            return "Waning Gibbous", "🌖"
        elif phase_percent >= 47 and phase_percent <= 53:
            return "Last Quarter", "🌗"
        elif phase_percent > 3 and phase_percent < 47:
            return "Waning Crescent", "🌘"
        elif phase_percent >= 97 or phase_percent <= 3:
            return "New Moon", "🌑"
        elif phase_percent > 3 and phase_percent < 47:
            return "Waxing Crescent", "🌒"
        elif phase_percent >= 47 and phase_percent <= 53:
            return "First Quarter", "🌓"
        else:
            return "Waxing Gibbous", "🌔"

    except Exception as e:
        logger.error(f"Error calculating moon phase: {str(e)}")
        return "Unable to calculate moon phase", "❓"

async def hi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /hi command for the default location (Herceg Novi)"""
    try:
        logger.info("Received /hi command, calculating moon phase...")
        phase_name, emoji = get_moon_phase()
        logger.info(f"Calculated phase: {phase_name} {emoji}")
        sunrise_time, sunset_time = get_sun_times()
        min_temp, max_temp, pressure, weather_description = await get_weather()

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
        logger.error(f"Error in hi_command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. Please try again later."
        )

async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle the /forecast command.
    The user should type: /forecast <city name>
    The bot will retrieve the forecast for the provided location.
    """
    try:
        if not context.args:
            await update.message.reply_text("Please provide a city name. Usage: /forecast <city>")
            return

        city_name = " ".join(context.args)
        min_temp, max_temp, pressure, weather_description = await get_weather(city=city_name)
        if all(v is not None for v in [min_temp, max_temp, pressure, weather_description]):
            forecast_message = (
                f"Forecast for {city_name}:\n"
                f"🌡 Weather: {weather_description}\n"
                f"❄️ Min Temp: {min_temp}°C\n"
                f"☀️ Max Temp: {max_temp}°C\n"
                f"🌬 Pressure: {pressure} hPa"
            )
        else:
            forecast_message = f"Weather data for {city_name} is currently unavailable."
        await update.message.reply_text(forecast_message)
    except Exception as e:
        logger.error(f"Error in forecast_command: {e}")
        await update.message.reply_text("Sorry, an error occurred while retrieving the forecast.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    try:
        logger.info("Received /start command, sending welcome message...")
        message = (
            "Hello! 👋\n\n"
            "I can provide weather data for Herceg Novi using /hi.\n"
            "Or type /forecast <city> to get the forecast for a specific location."
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. Please try again later."
        )

async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot"""
    error_message = f"Error: {context.error}"
    if update:
        error_message = f"Update {update} caused {error_message}"
    logger.error(error_message)
    try:
        if update is not None and update.message is not None:
            await update.message.reply_text("Sorry, something went wrong. Please try again later.")
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

def main() -> None:
    """Start the bot"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.critical("No token found! Make sure to set TELEGRAM_BOT_TOKEN environment variable.")
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    try:
        application = Application.builder().token(token).build()
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("hi", hi_command))
        application.add_handler(CommandHandler("forecast", forecast_command))
        application.add_error_handler(error_handler)
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Error starting bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()
