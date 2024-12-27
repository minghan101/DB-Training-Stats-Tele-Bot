from fastapi import FastAPI, Request
from telegram import Update
from bot import create_bot, init_db
from env import API_KEY, WEBHOOK_URL

app = FastAPI()
bot_app = create_bot()

@app.on_event("startup")
async def startup():
    await init_db()
    await bot_app.bot.set_webhook(WEBHOOK_URL)

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    if token != API_KEY:
        return {"error": "Invalid token"}
    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}
