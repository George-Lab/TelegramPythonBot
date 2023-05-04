"""
This is a echo bot.
It echoes any incoming text messages.
"""

import logging
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

# BOT TOKEN HERE
API_TOKEN = 'BOT TOKEN HERE'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# connect to the database
conn = sqlite3.connect("finance_tracker.db")
cursor = conn.cursor()

# create tables if they don't exist yet
cursor.execute(
    "CREATE TABLE IF NOT EXISTS spending_categories ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "name TEXT NOT NULL, "
    "user_id INTEGER NOT NULL"
    ")"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS income_sources ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "name TEXT NOT NULL, "
    "user_id INTEGER NOT NULL"
    ")"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS transactions ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, "
    "category VARCHAR(25) NOT NULL, "
    "type VARCHAR(25) NOT NULL, "
    "amount REAL NOT NULL, "
    "user_id INTEGER NOT NULL"
    ")"
)
conn.commit()

# Define an empty dictionary to store user input
user_data = {}

# predefined "General" category and source
general_category_name = "General"
general_source_name = "General"

# handle the /start command
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id

    # check if the user has the "General" spending category and add it if not
    rows = cursor.execute(
        "SELECT id FROM spending_categories "
        "WHERE name = ? AND user_id = ?",
        (general_category_name, user_id)
    ).fetchall()
    if not rows:
        cursor.execute(
            "INSERT INTO spending_categories (name, user_id) VALUES (?, ?)",
            (general_category_name, user_id)
        )
        conn.commit()

    # check if the user has the "General" income source and add it if not
    rows = cursor.execute(
        "SELECT id FROM income_sources "
        "WHERE name = ? AND user_id = ?",
        (general_source_name, user_id)
    ).fetchall()
    if not rows:
        cursor.execute(
            "INSERT INTO income_sources (name, user_id) VALUES (?, ?)",
            (general_source_name, user_id)
        )
        conn.commit()

    # ask the user what they want to do
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Add spending category", "Add income source")
    keyboard.add("Make a new record", "Show my records")

    await message.reply(
        "What do you want to do?",
        reply_markup=keyboard
    )

# handle the "Add spending category" option
@dp.message_handler(lambda message: message.text == "Add spending category", state="*")
async def add_spending_category(message: types.Message):
    user_id = message.from_user.id

    await message.reply("What's the name of the new category?")

    # wait for the user to input the name of the new category
    await dp.current_state(user=user_id).set_state("add_spending_category")

@dp.message_handler(state="add_spending_category")
async def add_spending_category_name(message: types.Message):

    user_id = message.from_user.id
    category_name = message.text.strip()

    # check if the category already exists
    rows = cursor.execute(
        "SELECT id FROM spending_categories "
        "WHERE name = ? AND user_id = ?",
        (category_name, user_id)
    ).fetchall()
    if len(rows) != 0:
        await message.reply("This category already exists.")
        await dp.current_state(user=user_id).set_state("choosing_action")
        return

    # add the new category to the database
    cursor.execute(
        "INSERT INTO spending_categories (name, user_id) VALUES (?, ?)",
        (category_name, user_id)
    )
    conn.commit()


    await message.reply(f"Category '{category_name}' has been added.")
    await dp.current_state(user=user_id).set_state("choosing_action")


# handle the "Add income source" option
@dp.message_handler(lambda message: message.text == "Add income source", state="*")
async def add_income_source(message: types.Message):
    user_id = message.from_user.id

    await message.reply("What's the name of the new income source?")

    # wait for the user to input the name of the new income source
    await dp.current_state(user=user_id).set_state("add_income_source")


@dp.message_handler(state="add_income_source")
async def add_income_source_name(message: types.Message):
    user_id = message.from_user.id
    source_name = message.text.strip()

    # check if the income source already exists
    rows = cursor.execute(
        "SELECT id FROM income_sources "
        "WHERE name = ? AND user_id = ?",
        (source_name, user_id)
    ).fetchall()
    if rows:
        await message.reply("This income source already exists.")
        await dp.current_state(user=user_id).set_state("choosing_action")
        return

    # add the new income source to the database
    cursor.execute(
        "INSERT INTO income_sources (name, user_id) VALUES (?, ?)",
        (source_name, user_id)
    )
    conn.commit()

    await message.reply(f"Income source '{source_name}' has been added.")
    await dp.current_state(user=user_id).set_state("choosing_action")


# handle the "Make a new record" option
@dp.message_handler(lambda message: message.text == "Make a new record", state="*")
async def make_new_record(message: types.Message):
    user_id = message.from_user.id

    # ask the user what type of record they want to add
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Spending", "Income")

    await message.reply(
        "What type of record do you want to add?",
        reply_markup=keyboard
    )

    # wait for the user to input the type of record they want to add
    await dp.current_state(user=user_id).set_state("make_new_record")


@dp.message_handler(state="make_new_record")
async def make_new_record_type(message: types.Message):
    user_id = message.from_user.id
    record_type = message.text.strip().lower()

    # validate the type of record
    if record_type not in ("spending", "income"):
        await message.reply("Invalid record type.")
        return
    user_data[message.chat.id] = {'record_type': record_type}

    # ask the user for the amount of the record
    await message.reply(f"What's the {record_type} amount?")

    # wait for the user to input the amount of the record
    await dp.current_state(user=user_id).set_state("make_new_record_amount")


@dp.message_handler(state="make_new_record_amount")
async def make_new_record_amount(message: types.Message):
    user_id = message.from_user.id
    amount = message.text.strip()

    try:
        amount = float(amount)
    except ValueError:
        await message.reply("Invalid amount.")
        return
    user_data[message.chat.id]['record_amount'] = amount

    # ask the user for the category or source of the record
    if user_data[message.chat.id]['record_type'] == 'spending':
        categories = cursor.execute(
            "SELECT id, name FROM spending_categories "
            "WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in categories:
            keyboard.add(category[1])

        await message.reply("Select a category:", reply_markup=keyboard)

        # wait for the user to select a category
        await dp.current_state(user=user_id).set_state("make_new_record_category")
    else:
        sources = cursor.execute(
            "SELECT id, name FROM income_sources "
            "WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for source in sources:
            keyboard.add(source[1])

        await message.reply("Select an income source:", reply_markup=keyboard)

        # wait for the user to select an income source
        await dp.current_state(user=user_id).set_state("make_new_record_source")

@dp.message_handler(state="make_new_record_category")
async def make_new_record_category(message: types.Message):
    user_id = message.from_user.id
    category_name = message.text.strip()

    # get the category id from the name
    row = cursor.execute(
        "SELECT id FROM spending_categories "
        "WHERE name = ? AND user_id = ?",
        (category_name, user_id)
    ).fetchone()

    if not row:
        await message.reply("Invalid category.")
        return
    user_data[message.chat.id]['record_category'] = category_name

    category_id = row[0]

    # add the record to the database
    cursor.execute(
        "INSERT INTO transactions (category, type, amount, user_id) VALUES (?, ?, ?, ?)",
        (user_data[message.chat.id]['record_category'], user_data[message.chat.id]['record_type'], user_data[message.chat.id]['record_amount'], message.chat.id)
    )
    conn.commit()

    await message.reply("Record added.")

    # reset the state
    await dp.current_state(user=user_id).reset_state()

@dp.message_handler(state="make_new_record_source")
async def make_new_record_source(message: types.Message):
    user_id = message.from_user.id
    source_name = message.text.strip()

    # get the source id from the name
    row = cursor.execute(
        "SELECT id FROM income_sources "
        "WHERE name = ? AND user_id = ?",
        (source_name, user_id)
    ).fetchone()

    if not row:
        await message.reply("Invalid income source.")
        return
    user_data[message.chat.id]['record_category'] = source_name

    source_id = row[0]

    # add the record to the database
    cursor.execute(
        "INSERT INTO transactions (category, type, amount, user_id) VALUES (?, ?, ?, ?)",
        (user_data[message.chat.id]['record_category'], user_data[message.chat.id]['record_type'], user_data[message.chat.id]['record_amount'], message.chat.id)
    )
    conn.commit()

    await message.reply("Record added.")

    # reset the state
    await dp.current_state(user=user_id).reset_state()

@dp.message_handler(lambda message: message.text == "Show my records")
async def show_records(message: types.Message):
    user_id = message.from_user.id

    print("""
        SELECT type, category, amount
        FROM transactions
        WHERE user_id=? AND type'spending' 
        ORDER BY id DESC 
        LIMIT 10 """, (user_id,)
          )

    # get the spending records
    rows = cursor.execute(f"SELECT type, category, amount FROM transactions WHERE user_id = {user_id} AND type='spending' ORDER BY id DESC LIMIT 10 ").fetchall()

    if rows:
        spending_text = "Spending records:\n\n"
        for row in rows:
            spending_text += f"{row[0]}::{row[1]} {row[2]}\n"
    else:
        spending_text = "No spending records."

    # get the income records
    rows = cursor.execute(f"SELECT type, category, amount FROM transactions WHERE user_id = {user_id} AND type='income' ORDER BY id DESC LIMIT 10 ").fetchall()

    if rows:
        income_text = "Income records:\n\n"
        for row in rows:
            income_text += f"{row[0]}::{row[1]} {row[2]}\n"
    else:
        income_text = "No income records."

    await message.reply(spending_text + "\n" + income_text)



@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id

    cursor.execute(
        "INSERT OR IGNORE INTO spending_categories (name, user_id) VALUES (?, ?)",
        ("General", user_id)
    )
    cursor.execute(
        "INSERT OR IGNORE INTO income_sources (name, user_id) VALUES (?, ?)",
        ("General", user_id)
    )
    conn.commit()

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Add spending category", "Add income source", "Make a new record", "Show my records")

    await message.reply(
        "Welcome to the personal finance tracker bot!\n"
        "What do you want to do?",
        reply_markup=keyboard
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

