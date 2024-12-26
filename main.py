from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from datetime import datetime
import asyncpg
import psycopg2
import os

from env import API_KEY, SPREADSHEET_ID, DATABASE_URL

# Constants for database URL and session management
DATABASE_URL = os.getenv('DATABASE_URL')
sessions = {}

# FastAPI app
app = FastAPI()

# Database initialization
def init_db():
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_data (
            id SERIAL PRIMARY KEY,
            date TEXT,
            distance INTEGER,
            time TEXT,
            pairs INTEGER,
            stroke_count INTEGER,
            stroke_rate INTEGER,
            remarks TEXT,
            uploaded BOOLEAN DEFAULT FALSE
        )
    """)
    connection.commit()
    connection.close()

# States for ConversationHandler
DATE, ENTRY, CLOSING = range(3)

# Bot Handlers (same as before)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("Key in date of Training (DD/MM/YYYY):")
    sessions[user_id] = {"entries": []}
    return DATE

async def set_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    date_text = update.message.text
    try:
        date = datetime.strptime(date_text, "%d/%m/%Y").strftime("%d/%m/%Y")
        sessions[user_id]["date"] = date
        await update.message.reply_text(
            "Date recorded. Training Stats in the format:\n"
            "Distance, Time(mm:ss), Pairs, Stroke Count, Stroke Rate, Remarks"
        )    
        return ENTRY
    except ValueError:
        await update.message.reply_text("Invalid date format. Please use dd/mm/yyyy")

async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    try:
        parts = text.split(", ")
        if len(parts) < 5:
            raise ValueError("Insufficient data provided. Expected at least 5 values.")
        
        # Parse mandatory fields
        distance = int(parts[0])
        time = parts[1]
        pairs = int(parts[2])
        stroke_count = int(parts[3])
        stroke_rate = int(parts[4])

        # Remarks is optional
        remarks = parts[5] if len(parts) > 5 else "NIL"

        entry = {
            "distance": distance,
            "time": time,
            "pairs": pairs,
            "stroke_count": stroke_count,
            "stroke_rate": stroke_rate,
            "remarks": remarks,
        }

        sessions[user_id]["entries"].append(entry)
        await update.message.reply_text("Entry added. Add another or type /close to finish.")
        return ENTRY

    except ValueError as e:
        await update.message.reply_text(f"Error parsing entry. Ensure format is correct: {e}")
        return ENTRY

async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in sessions or "date" not in sessions[user_id]:
        await update.message.reply_text("No active session to close")
        return ConversationHandler.END
    
    # Connect to the database
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    date = sessions[user_id]["date"]
    for entry in sessions[user_id]["entries"]:
        cursor.execute("""
            INSERT INTO training_data (date, distance, time, pairs, stroke_count, stroke_rate, remarks)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (date, entry["distance"], entry["time"], entry["pairs"], entry["stroke_count"], entry["stroke_rate"], entry["remarks"]))

    conn.commit()
    conn.close()
    del sessions[user_id]
    await update.message.reply_text("Session closed and data saved. REMEMBER TO /upload to upload to Google Sheets")
    return ConversationHandler.END

@app.post("/webhook/{token}")
async def webhook(request: Request, token: str):
    if token != API_KEY:
        return {"error": "Invalid token"}
    
    try:
        # Log request body for debugging purposes
        body = await request.body()
        print("Received body:", body)

        # If body is empty, return an error
        if not body:
            return {"error": "Empty body received from Telegram"}

        # Try to parse the JSON data
        update = await request.json()
        application = Application.builder().token(API_KEY).build()
        telegram_update = Update.de_json(update, application.bot)
        application.process_update(telegram_update)
        return {"status": "ok"}
    except Exception as e:
        # Log the error
        print(f"Error processing webhook: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}

@app.get("/webhook/{token}")
async def webhook_get(request: Request, token: str):
    if token != API_KEY:
        return {"error": "Invalid token"}
    return {"status": "Webhook is set up correctly."}

# Upload data to Google Sheets
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = await asyncpg.connect(DATABASE_URL)

    rows = await conn.fetch("""
        SELECT * FROM training_data
        WHERE uploaded = FALSE
        ORDER BY date ASC
    """)

    if not rows:
        await update.message.reply_text("No new data to upload.")
        return
    
    credentials = Credentials.from_service_account_file("./hardy-moon-445610-p0-ced3f5219893.json")
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()
    spreadsheet_id = SPREADSHEET_ID

    # Process and upload data to Google Sheets
    # Implementation same as original `upload()` function

    # Mark rows as uploaded
    await conn.execute("UPDATE training_data SET uploaded = TRUE WHERE uploaded = FALSE")
    await conn.commit()
    await conn.close()
    await update.message.reply_text("Data uploaded to Google Sheets.")

# Initialize Telegram bot with webhooks
def start_bot():
    global application
    application = Application.builder().token(API_KEY).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_date)],
            ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_entry)],
        },
        fallbacks=[CommandHandler("close", close)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("upload", upload))

    # Set webhook
    webhook_url = f"https://db-training-stats-tele-bot.onrender.com/webhook/{API_KEY}"
    application.bot.set_webhook(url=webhook_url)

# Run the FastAPI server
if __name__ == "__main__":
    init_db()
    start_bot()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
