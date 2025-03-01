# Weather Telegram Bot - Project Memory

## Project Structure
- main.py - Main application logic for the Telegram bot
- todolist.md - Markdown file containing the to-do list
- memory.md - Markdown file containing project memory and notes
- .env.example - Example environment variables
- Procfile - Procfile for deploying the bot
- pyproject.toml - Project configuration file
- replit.nix - Replit configuration file
- uv.lock - Lock file for dependencies

## Application Design
- Telegram bot providing weather and moon phase information for Herceg Novi.
- Uses Weatherbit API for weather data.
- Uses Telegram Bot API for bot functionality.
- Fetches weather data (min/max temperature, pressure, weather description) and moon data (moonrise, moonset, moon phase) for Herceg Novi.
- Responds to /hi and /start commands with weather and moon phase information.

## Implementation Notes
- Uses `python-telegram-bot` library for Telegram bot functionality.
- Uses `httpx` library for making HTTP requests to the Weatherbit API.
- Uses `python-dotenv` library for loading environment variables from a .env file.
- Uses logging for error handling and debugging.
- Includes a function `get_moon_phase_name` to convert moon phase numerical value to a text description.
- The `get_weather_and_moon_data` function fetches weather and moon data from the Weatherbit API.
- The `hi_command` function handles the /hi command and sends weather and moon phase information to the user.
- The `main` function starts the bot and adds command handlers.
- Implemented error handling for the Weatherbit API requests in the `get_weather_and_moon_data` function.
- Added tests for the error handling in the `tests/test_main.py` file.
- Added a test case to `tests/test_main.py` to check if the moon data is working correctly when the API returns valid data.
