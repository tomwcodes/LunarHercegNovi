import os
import logging
from typing import Union, Optional
import ephem  # type: ignore
from datetime import datetime
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

# Herceg Novi coordinates
HERCEG_NOVI_LAT = 42.4531
HERCEG_NOVI_LON = 18.5375

async def get_weather() -> tuple[Optional[float], Optional[float], Optional[float], Optional[str]]:
    """
    Get current weather data for Herceg Novi from Weatherbit
    Returns: tuple(min_temp, max_temp, pressure, description) or (None, None, None, None) if error
    """
    try:
        api_key = os.getenv('WEATHERBIT_API_KEY')
        if not api_key:
            logger.error("Weatherbit API key not found in environment variables")
            return None, None, None, None

        # Add days parameter and specify units as metric
        url = f"https://api.weatherbit.io/v2.0/forecast/daily?lat={HERCEG_NOVI_LAT}&lon={HERCEG_NOVI_LON}&key={api_key}&days=1"

        if os.getenv('ENVIRONMENT') != 'production':
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
                # Log response structure without sensitive data
                safe_data = {k: v for k, v in data.items() if k != 'data'}
                logger.info(f"API Response structure: {safe_data}")

            if 'data' in data and len(data['data']) > 0:
                today_data = data['data'][0]
                # Round temperatures to one decimal place
                min_temp = round(float(today_data['min_temp']), 1) if 'min_temp' in today_data else None
                max_temp = round(float(today_data['max_temp']), 1) if 'max_temp' in today_data else None

                if os.getenv('ENVIRONMENT') != 'production':
                    logger.info(f"Weather data retrieved:")
                    logger.info(f"Min temperature: {min_temp}°C")
                    logger.info(f"Max temperature: {max_temp}°C")

                # Get pressure data (in mb/hPa)
                pressure = round(float(today_data['pres']), 1) if 'pres' in today_data else None
                # Get weather description from the weather array
                description = today_data['weather'][0]['description'] if 'weather' in today_data and today_data['weather'] else None

                if os.getenv('ENVIRONMENT') != 'production':
                    logger.info(f"Pressure: {pressure} hPa")
                    logger.info(f"Weather: {description}")

                return min_temp, max_temp, pressure, description
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
    Calculate sunrise and sunset times for Herceg Novi
    Args:
        custom_date: Optional datetime object for testing specific dates
    Returns: tuple(sunrise_time, sunset_time)
    """
    try:
        # Create observer for Herceg Novi
        observer = ephem.Observer()
        observer.lat = str(HERCEG_NOVI_LAT)  # ephem expects string in degrees
        observer.lon = str(HERCEG_NOVI_LON)
        observer.elevation = 10  # meters above sea level
        observer.pressure = 0  # disable refraction calculation
        observer.horizon = '-0:34'  # standard altitude of the sun's center when it rises/sets

        # Set the date
        now = custom_date if custom_date else datetime.utcnow()
        observer.date = ephem.Date(now)

        # Log settings in non-production environment
        if os.getenv('ENVIRONMENT') != 'production':
            logger.info(f"Sun Times Calculation:")
            logger.info(f"Observer lat: {observer.lat}")
            logger.info(f"Observer lon: {observer.lon}")
            logger.info(f"Observer elevation: {observer.elevation}")
            logger.info(f"Current Date (UTC): {now}")

        # Calculate sun rise/set times
        sun = ephem.Sun()
        sun.compute(observer)
        try:
            # Get next rising and setting times
            next_rising = observer.next_rising(sun)
            next_setting = observer.next_setting(sun)

            if os.getenv('ENVIRONMENT') != 'production':
                logger.info(f"Raw next rising: {next_rising}")
                logger.info(f"Raw next setting: {next_setting}")

            # Convert ephem.Date to Python datetime and add UTC+1 offset
            from datetime import timedelta
            sunrise_local = ephem.Date(next_rising).datetime() + timedelta(hours=1)
            sunset_local = ephem.Date(next_setting).datetime() + timedelta(hours=1)
        except ephem.CircumpolarError:
            logger.error("Sun is circumpolar at this location and date")
            return "No sunrise", "No sunset"

        # Format times as strings
        sunrise_str = sunrise_local.strftime('%H:%M')
        sunset_str = sunset_local.strftime('%H:%M')

        if os.getenv('ENVIRONMENT') != 'production':
            logger.info(f"Formatted sunrise: {sunrise_str}")
            logger.info(f"Formatted sunset: {sunset_str}")

        return sunrise_str, sunset_str

    except Exception as e:
        logger.error(f"Error calculating sun times: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        return "Unknown", "Unknown"

def get_moon_phase(custom_date: Optional[datetime] = None) -> tuple:
    """
    Calculate the current moon phase for Herceg Novi
    Args:
        custom_date: Optional datetime object for testing specific dates
    Returns: tuple(phase_name, emoji)
    """
    try:
        # Create observer for Herceg Novi
        observer = ephem.Observer()
        observer.lat = str(HERCEG_NOVI_LAT)  # ephem expects string in degrees
        observer.lon = str(HERCEG_NOVI_LON)
        observer.elevation = 10  # meters above sea level

        # Get current moon information
        moon = ephem.Moon()
        moon.compute(observer)

        # Use custom_date if provided, otherwise use current UTC time
        current_date = ephem.Date(custom_date) if custom_date else ephem.Date(datetime.utcnow())

        # Calculate previous and next new moons
        previous_new = ephem.previous_new_moon(current_date)
        next_new = ephem.next_new_moon(current_date)

        # Calculate moon's age (days since last new moon)
        moon_age = current_date - previous_new
        moon_cycle = next_new - previous_new

        # Calculate phase percentage (0-100)
        phase_percent = (moon_age / moon_cycle) * 100

        # Log phase calculation details in non-production environment
        if os.getenv('ENVIRONMENT') != 'production':
            logger.info(f"Moon Phase Calculation:")
            logger.info(f"Current Date (UTC): {ephem.Date(current_date).datetime()}")
            logger.info(f"Previous New Moon: {ephem.Date(previous_new).datetime()}")
            logger.info(f"Next New Moon: {ephem.Date(next_new).datetime()}")
            logger.info(f"Moon Age (days): {moon_age * 29.53}")
            logger.info(f"Moon Cycle (days): {moon_cycle * 29.53}")
            logger.info(f"Phase Percentage: {phase_percent}%")
            logger.info(f"Moon Phase: {moon.phase}")

        # Fixed phase percentage ranges for accurate detection
        if phase_percent >= 97 or phase_percent <= 3:  # Full moon
            return "Full Moon", "🌕"
        elif phase_percent > 50 and phase_percent < 97:  # Waning Gibbous
            return "Waning Gibbous", "🌖"
        elif phase_percent >= 47 and phase_percent <= 53:  # Last Quarter
            return "Last Quarter", "🌗"
        elif phase_percent > 3 and phase_percent < 47:  # Waning Crescent
            return "Waning Crescent", "🌘"
        elif phase_percent >= 97 or phase_percent <= 3:  # New moon
            return "New Moon", "🌑"
        elif phase_percent > 3 and phase_percent < 47:  # Waxing Crescent
            return "Waxing Crescent", "🌒"
        elif phase_percent >= 47 and phase_percent <= 53:  # First Quarter
            return "First Quarter", "🌓"
        else:  # Waxing Gibbous
            return "Waxing Gibbous", "🌔"

    except Exception as e:
        logger.error(f"Error calculating moon phase: {str(e)}")
        return "Unable to calculate moon phase", "❓"

async def hi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /hi command"""
    try:
        # Log before calculating phase
        logger.info("Received /hi command, calculating moon phase...")

        # Use current date for production
        phase_name, emoji = get_moon_phase()

        # Log after calculating phase
        logger.info(f"Calculated phase: {phase_name} {emoji}")

        # Get sunrise and sunset times
        sunrise_time, sunset_time = get_sun_times()

        # Get weather data
        min_temp, max_temp, pressure, description = await get_weather()

        # Format message with location, date, sun times, temperature, pressure, weather description, sunset, and moon phase
        current_date = datetime.now().strftime('%A %d/%m')
        temp_info = f"Min Temp: {min_temp}°C\nMax Temp: {max_temp}°C\nPressure: {pressure} hPa\nWeather: {description}" if min_temp is not None and max_temp is not None and pressure is not None and description is not None else "Weather data currently unavailable"
        message = (
            f"Herceg Novi, {current_date}:\n"
            f"Sunrise: {sunrise_time}\n"
            f"{temp_info}\n"
            f"Sunset: {sunset_time}\n"
            f"Moon Phase: {phase_name} {emoji}"
        )

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in hi_command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. "
            "Please try again later."
        )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    try:
        logger.info("Received /start command, sending welcome message...")
        message = (
            f"Hello! 👋\n\n"
            f"I can provide weather data for Herceg Novi. Just say /hi"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. "
            "Please try again later."
        )

async def error_handler(update: Optional[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot"""
    # Log the error with update information if available
    error_message = f"Error: {context.error}"
    if update:
        error_message = f"Update {update} caused {error_message}"
    logger.error(error_message)

    try:
        # Only attempt to reply if we have a valid update with a message
        if update is not None and update.message is not None:
            await update.message.reply_text(
                "Sorry, something went wrong. Please try again later."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

def main() -> None:
    """Start the bot"""
    # Get the token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.critical("No token found! Make sure to set TELEGRAM_BOT_TOKEN environment variable.")
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

    try:
        # Create application
        application = Application.builder().token(token).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("hi", hi_command))

        # Add error handler
        application.add_error_handler(error_handler)

        # Start the bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Error starting bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()
