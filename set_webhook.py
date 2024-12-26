import asyncio
from telegram import Bot
from env import API_KEY

async def set_webhook():
    bot = Bot(token=API_KEY)
    await bot.set_webhook(url=f"https://MH.pythonanywhere.com/{API_KEY}")
    print("Webhook set!")

# Run the asynchronous function
if __name__ == "__main__":
    asyncio.run(set_webhook())
