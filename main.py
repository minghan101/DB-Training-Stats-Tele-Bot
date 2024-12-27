from fastapi import FastAPI, Request
from fastapi_lifespan_manager import LifespanManager, State
from telegram import Update
from bot import create_bot, init_db
from env import API_KEY, WEBHOOK_URL

# Create the bot instance
bot_app = create_bot()

# Create a LifespanManager
app = LifespanManager()

@app.lifespan
async def startup_shutdown():
    # Startup tasks
    await init_db()
    await bot_app.bot.set_webhook(WEBHOOK_URL)
    yield  # Run the application
    # Shutdown tasks (if needed, add here)

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    if token != API_KEY:
        return {"error": "Invalid token"}
    
    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}
