# NUSDB Training Bot 🚣‍♂️🤖

## Overview 🌟

NUSDB Training Bot is a Python-based Telegram bot that helps users log their training sessions and upload the data to Google Sheets. It allows users to input various training metrics, such as distance, time, pairs, stroke count, and stroke rate, as well as optional remarks.

The bot stores the data in an SQLite database and provides commands to upload the recorded data to Google Sheets.

## Main Idea 💡
1.	Create an easy-to-use Telegram Bot to log training sessions
2.	Will start a new session upon `/start` command
3.	Will prompt user for `date` in dd/mm/yyyy format -> This will contribute to one Training session entry in the database
4.	Then prompt the user for the following training data:
         Distance, Time (mm:ss), Pairs, Stroke Count, Stroke Rate, Remarks. The columns can be empty.
  	This will contribute to one entry under the “date”. There can be more entries on the same date
6.	When the user type `/close` command, the bot will close the entry for the date itself.
7.	When given the command `/upload`, the database will upload any new data not uploaded into a specific googlesheet of my choice.

**Additional Information:**
- Hosted on **PythonAnywhere** online server 🌐.
- Data is assumed to be added chronologically 📅.
- Data is not deleted and is assumed to be correct ✅.

## Features 🚀

- **Session Management**: Start a new session, record training entries, and close the session.
- **Google Sheets Integration**: Upload training data to Google Sheets for further analysis and tracking.
- **Data Management**: Reset the upload status and reorder the database based on the training date.
- **Flexibility**: Optional fields for stroke rate and remarks.

## Installation ⚙️
1. Install required dependencies:
    ```bash
    pip install python-telegram-bot google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
    ```
    
2. Clone this repository or copy the bot's script.

3. Set up your **Google Sheets API** credentials:
    - Follow the [Google Sheets API guide](https://developers.google.com/sheets/api/quickstart/python) to create a Google Cloud project and enable the Sheets API.
    - Create a service account and download the JSON credentials file, place it in the same directory as your project folder
    - Save the credentials file in your project directory as `[CREDENTIAL_FILE_NAME].json`.

4. On Telegram, go to BotFather:
    - `/start`
    - `/newbot`
    - Name your bot
    - `/setcommands` & key in your bot's telegram handle. 🧑‍💻
    
5. Set up environment variables in your `.env` file:
    ```env
    API_KEY=your_telegram_bot_api_key
    SPREADSHEET_ID=your_spreadsheet_id
    ```

## How to Use 🛠️

### Commands 📜

- `/start` – Start a new training session 🏁
- `/close` – Close the current training session and save the data 💾
- `/upload` – Upload the training data to Google Sheets 📤
- `/reorder` – Reorder the database by date (ascending order) 🔄
- `/reset_upload` – Reset the uploaded status of the data 🔄

### Training Data Format 📝
When adding a training entry, follow this format: Distance, Time(mm:ss), Pairs, Stroke Count, Stroke Rate, Remarks
- **Distance**: The distance of the training in meters (e.g., 1000).
- **Time**: The time taken for the training (e.g., 5:01 for 5 minutes and 1 second).
- **Pairs**: The number of pairs during the training (e.g., 8).
- **Stroke Count**: The total number of strokes during the training (e.g., 243).
- **Stroke Rate**: The rate of strokes per minute (e.g., 48).
- **Remarks**: Optional field for any additional comments (e.g., "Headwind Set"). If omitted, defaults to "NIL".
Output:
`1000, 5:01, 8, 243, 48, Headwind Set`

### Session Workflow 🔄:

1. **Start a session**: Use `/start` to begin a new session. The bot will prompt for the training date.
2. **Add entries**: For each entry, input the training data in the format mentioned above.
3. **Close the session**: Type `/close` to save the entries to the database.
4. **Upload data**: Use `/upload` to upload the recorded data to Google Sheets.
5. **Reorder data**: Use `/reorder` to reorder the database based on date (ascending).
6. **Reset upload status**: If you need to reset the upload status, use `/reset_upload`.

## Database Schema 🗃️

The data is stored in an SQLite database (`training_data.db`) with the following schema:

```sql
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
);
```

## License 📜
This project is licensed under the [Apache License 2.0](http://www.apache.org/licenses/LICENSE-2.0).




