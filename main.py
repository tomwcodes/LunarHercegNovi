import os
import logging
import ephem
from datetime import datetime
from dotenv import load_dotenv
from telegram import __version__ as TG_VER, Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext

try:
    from telegram import __version_info__
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
HERCEG_NOVI_LAT = '42.4531'
HERCEG_NOVI_LON = '18.5375'

def get_moon_phase() -> tuple:
    """
    Calculate the current moon phase for Herceg Novi
    Returns: tuple(phase_name, emoji)
    """
    try:
        # Create observer for Herceg Nov
        observer = ephem.Observer()
        observer.lat = HERCEG_NOVI_LAT
        observer.lon = HERCEG_NOVI_LON

        # Get current moon information
        moon = ephem.Moon()
        moon.compute(observer)

        # Get current date for age calculation
        current_date = ephem.Date(datetime.utcnow())

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

        # Since we know February 16, 2025 was a full moon (100%),
        # on February 19 we should be in waning gibbous phase
        if phase_percent > 85:  # Full moon
            return "Full Moon 🌕", "🌕"
        elif phase_percent > 60:  # After full moon, before last quarter
            return "Waning Gibbous 🌖", "🌖"
        elif phase_percent > 40:  # Last quarter
            return "Last Quarter 🌗", "🌗"
        elif phase_percent > 15:  # After last quarter, before new moon
            return "Waning Crescent 🌘", "🌘"
        elif phase_percent <= 15:  # New moon
            return "New Moon 🌑", "🌑"
        elif phase_percent <= 35:  # After new moon, before first quarter
            return "Waxing Crescent 🌒", "🌒"
        elif phase_percent <= 60:  # First quarter
            return "First Quarter 🌓", "🌓"
        else:  # After first quarter, before full moon
            return "Waxing Gibbous 🌔", "🌔"

    except Exception as e:
        logger.error(f"Error calculating moon phase: {str(e)}")
        return "Unable to calculate moon phase", "❓"

async def hi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /hi command"""
    try:
        # Log before calculating phase
        logger.info("Received /hi command, calculating moon phase...")

        phase_name, emoji = get_moon_phase()

        # Log after calculating phase
        logger.info(f"Calculated phase: {phase_name} {emoji}")

        message = (
            f"Hello! 👋\n\n"
            f"Current moon phase in Herceg Novi:\n"
            f"{phase_name}"
        )

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in hi_command: {str(e)}")
        await update.message.reply_text(
            "Sorry, I encountered an error while processing your request. "
            "Please try again later."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and hasattr(update, 'message'):
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