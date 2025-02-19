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

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
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
        # Create observer for Herceg Novi
        observer = ephem.Observer()
        observer.lat = HERCEG_NOVI_LAT
        observer.lon = HERCEG_NOVI_LON

        # Get current moon information
        moon = ephem.Moon()
        moon.compute(observer)

        # Calculate moon phase
        phase = moon.phase

        # Determine moon phase and emoji
        if phase < 6.25:
            return "New Moon 🌑", "🌑"
        elif phase < 43.75:
            return "Waxing Crescent 🌒", "🌒"
        elif phase < 56.25:
            return "First Quarter 🌓", "🌓"
        elif phase < 93.75:
            return "Waxing Gibbous 🌔", "🌔"
        elif phase < 106.25:
            return "Full Moon 🌕", "🌕"
        elif phase < 143.75:
            return "Waning Gibbous 🌖", "🌖"
        elif phase < 156.25:
            return "Last Quarter 🌗", "🌗"
        elif phase < 193.75:
            return "Waning Crescent 🌘", "🌘"
        else:
            return "New Moon 🌑", "🌑"
    except Exception as e:
        logger.error(f"Error calculating moon phase: {str(e)}")
        return "Unable to calculate moon phase", "❓"

async def hi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /hi command"""
    try:
        phase_name, emoji = get_moon_phase()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = (
            f"Hello! 👋\n\n"
            f"Current moon phase in Herceg Novi:\n"
            f"{phase_name}\n\n"
            f"Time: {current_time}\n"
            f"Location: Herceg Novi, Montenegro"
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
        logger.error("No token found! Make sure to set TELEGRAM_BOT_TOKEN environment variable.")
        return

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
        logger.error(f"Error starting bot: {str(e)}")

if __name__ == '__main__':
    main()