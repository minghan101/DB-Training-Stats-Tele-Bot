# From the python-telegram-bot library -> pip install python-telegram-bot
from telegram.ext import Application, MessageHandler, filters, ConversationHandler, CommandHandler, ContextTypes
from telegram import Update
import sqlite3
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from env import API_KEY, SPREADSHEET_ID, DATABASE_URL
import psycopg2
import asyncpg

'''
SCHEMA: {
    date (string)
    distance (integer)
    time (string)
    pairs (integer)
    stroke_count (integer)
    stroke_rate (integer)
    remarks (text)
    uploaded (boolean) -> Indicates whether the data is uploaded to Google Sheets.
}
'''

#Constants
#DATABASE = "training_data.db"

#States for ConversationHandler
DATE, ENTRY, CLOSING = range(3)

'''
#Set up database
def init_db():
    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS training_data (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       date TEXT,
                       distance INTEGER,
                       time TEXT,
                       pairs INTEGER,
                       stroke_count INTEGER,
                       stroke_rate INTEGER,
                       remarks TEXT,
                       uploaded BOOLEAN default 0
                   )
                   """
    )
    connection.commit()
    connection.close()
'''

async def init_db():
    connection = await psycopg2.connect(DATABASE_URL)
    await connection.execute("""
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
    await connection.close()

# Handlers
sessions = {} #Initialize a dictionary for storing the session

# Starting a session
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("Key in date of Training (DD/MM/YYYY):  \n Eg. 25/12/2024 ")
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
            "Distance, Time(mm:ss), Pairs, Stroke Count, Stroke Rate, Remarks \n"
            "eg. 1000, 4:00, 10, 260, 72, down"
        )    
        return ENTRY
    except ValueError:
        await update.message.reply_text("Invalid date format. Please use DD/MM/YYYY \n Eg. 25/12/2024")
   
async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    try:
        # Split the input and handle missing remarks
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

        # Create entry
        entry = {
            "distance": distance,
            "time": time,
            "pairs": pairs,
            "stroke_count": stroke_count,
            "stroke_rate": stroke_rate,
            "remarks": remarks,
        }

        # Add entry to session
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
    
    conn = await asyncpg.connect(DATABASE_URL)
    date = sessions[user_id]["date"]
    for entry in sessions[user_id]["entries"]:
        await conn.execute("""
                       INSERT INTO training_data (date, distance, time, pairs, stroke_count, stroke_rate, remarks)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       """, (date, entry["distance"], entry["time"], entry["pairs"], entry["stroke_count"], entry["stroke_rate"], entry["remarks"]) 
                       )
    await conn.close()
    del sessions[user_id]
    await update.message.reply_text("Session closed. Use /upload to sync data to Google Sheets.")
    return ConversationHandler.END

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Connect to PostgreSQL database
    conn = await asyncpg.connect(DATABASE_URL)
        
    # Fetch all rows that have not been uploaded yet
    rows = await conn.fetch("""
        SELECT * FROM training_data 
        WHERE uploaded = FALSE 
        ORDER BY date ASC
    """)
    
    if not rows:
        await update.message.reply_text("No new data to upload.")
        return
    
    # Google Sheets set up
    credentials = Credentials.from_service_account_file("./hardy-moon-445610-p0-ced3f5219893.json")
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()
    spreadsheet_id = SPREADSHEET_ID
    
    # Group rows by date for session-based uploading
    sessions = {}
    for row in rows:
        date = row["date"]  # Assuming 'date' is the second column
        if date not in sessions:
            sessions[date] = []
        sessions[date].append(row)

    # Process each session
    for date, session_rows in sessions.items():
        # Determine the sheet name based on the month
        session_date = datetime.strptime(date, "%Y-%m-%d") # PostgreSQL uses ISO date format
        sheet_name = session_date.strftime("%m/%Y")
        
        # Check if the sheet exists, create if not
        try:
            sheet_metadata = sheet.get(spreadsheetId=spreadsheet_id).execute()
            sheets = [s['properties']['title'] for s in sheet_metadata.get('sheets', [])]
            if sheet_name not in sheets:
                # Add new sheet for the month
                sheet.batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        "requests": [
                            {
                                "addSheet": {
                                    "properties": {
                                        "title": sheet_name
                                    }
                                }
                            }
                        ]
                    }
                ).execute()
        except Exception as e:
            await update.message.reply_text(f"Error checking/creating sheet: {e}")
            return
        
        # Prepare data for upload
        values = [["Date", "Distance", "Time", "Pairs", "Stroke Count", "Stroke Rate", "Remarks"]]
        for row in session_rows:
            #values.append(row[1:-1])  # Exclude ID and uploaded flag
            values.append([row["date"], row["distance"], row["time"], row["pairs"], 
                           row["stroke_count"], row["stroke_rate"], row["remarks"]])
            
            
        # Determine the range (append to the sheet)
        range_ = f"{sheet_name}!A1"
        
        # Upload data
        try:
            spacing_body = {"values": [[""] * len(values[0])]}
            sheet.values().append(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
                valueInputOption="RAW",
                body= spacing_body
            ).execute()

            # Add spacing row
            spacing_body = {"values": [[""] * len(values[0])]}
            sheet.values().append(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
                valueInputOption="RAW",
                body= {"values": values}
            ).execute()
        except Exception as e:
            await update.message.reply_text(f"Error uploading data: {e}")
            return

    # Mark all rows as uploaded
    await conn.execute("UPDATE training_data SET uploaded = TRUE WHERE uploaded = FALSE")
    await conn.commit()
    await conn.close()
    await update.message.reply_text("Data uploaded to Google Sheets.")
    
### Reset the upload statuses ###
async def reset_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Connect to PostgreSQL database
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Execute query to reset the upload statuses
        await conn.execute("""
            UPDATE training_data 
            SET uploaded = FALSE 
            WHERE uploaded = TRUE
        """)
        
        # Close the connection to release resources
        await conn.close()
        
        # Notify the user
        await update.message.reply_text("Uploaded status has been reset.")
    except Exception as e:
        # Handle errors and notify the user
        await update.message.reply_text(f"An error occurred: {e}")
    

async def reorder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Connect to PostgreSQL database
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Execute query to fetch and reorder data by date (PostgreSQL handles dates natively)
        rows = await conn.fetch("""
            SELECT * FROM training_data 
            ORDER BY date::DATE ASC
        """)
        
        # Close the connection to release resources
        await conn.close()
        
        # Process and respond to the results
        if rows:
            await update.message.reply_text("Data re-ordered successfully.")
        else:
            await update.message.reply_text("No data found to reorder.")
    except Exception as e:
        # Handle errors and notify the user
        await update.message.reply_text(f"An error occurred: {e}")

def create_bot():
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
    return application