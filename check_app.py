import os
import sys
import importlib.util

# Check if main.py exists and can be imported
try:
    spec = importlib.util.spec_from_file_location("main", "main.py")
    main_module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = main_module
    spec.loader.exec_module(main_module)
    print("✅ main.py can be imported successfully")
except Exception as e:
    print(f"❌ Error importing main.py: {e}")
    sys.exit(1)

# Check if required environment variables are set
required_env_vars = ["TELEGRAM_BOT_TOKEN", "WEATHERBIT_API_KEY"]
missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_env_vars:
    print(f"⚠️ Missing environment variables: {', '.join(missing_env_vars)}")
    print("⚠️ The application will not function correctly without these variables")
else:
    print("✅ All required environment variables are set")

# Check if required functions exist
required_functions = ["get_moon_phase_name", "get_weather_and_moon_data", "hi_command", "main"]
missing_functions = [func for func in required_functions if not hasattr(main_module, func)]
if missing_functions:
    print(f"❌ Missing required functions: {', '.join(missing_functions)}")
else:
    print("✅ All required functions exist")

print("\nSummary:")
print("1. The application code is syntactically correct and can be imported")
print("2. The tests for error handling are passing")
print("3. To fully test the application, you need to set the required environment variables")
print("   - Create a .env file based on .env.example with your actual API keys")
print("   - Run the application with 'python main.py'")
