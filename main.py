from fastapi import FastAPI, Request
from fastapi.events import Lifespan
from telegram import Update
from bot import create_bot, init_db
from env import API_KEY, WEBHOOK_URL

# Create the bot instance
bot_app = create_bot()

# Create the FastAPI application with a custom lifespan manager
def app_lifespan():
    async def lifespan(app: FastAPI):
        # Startup tasks
        await init_db()
        await bot_app.bot.set_webhook(WEBHOOK_URL)
        yield  # Application is running
        # Shutdown tasks (if needed, add here)
    return lifespan

app = FastAPI(lifespan=app_lifespan())

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    if token != API_KEY:
        return {"error": "Invalid token"}
    
    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}
