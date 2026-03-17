# Xentera Telegram Bot

A simple Telegram bot named Xentera built with Python and the python-telegram-bot library.

## Features

- Basic command handling (/start, /help, /about)
- Message echoing
- Error handling and logging
- Environment-based configuration

## Setup

1. **Clone or download this project**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get a Telegram Bot Token:**
   - Talk to [@BotFather](https://t.me/BotFather) on Telegram
   - Create a new bot with the `/newbot` command
   - Copy the bot token

4. **Configure the bot:**
   ```bash
   cp .env.example .env
   ```
   - Edit `.env` and replace `your_bot_token_here` with your actual bot token

5. **Run the bot:**
   ```bash
   python bot.py
   ```

## Commands

- `/start` - Start the bot and see welcome message
- `/help` - Show available commands and help
- `/about` - Information about the bot

## Project Structure

```
windsurf-project-2/
├── bot.py              # Main bot application
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md          # This file
```

## Dependencies

- `python-telegram-bot` - Telegram bot framework
- `python-dotenv` - Environment variable management
- `requests` - HTTP library (dependency of python-telegram-bot)

## Extending the Bot

You can easily extend this bot by adding new command handlers in `bot.py`. For example:

```python
async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This is a custom command!")

# Add this to the main() function:
application.add_handler(CommandHandler("custom", custom_command))
```

## License

This project is open source and available under the MIT License.
