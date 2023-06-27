import sqlite3
from telegram.ext import Updater, CommandHandler, Job
import datetime

# Verbinding maken met de SQLite-database
conn = sqlite3.connect('database.db')
conn.execute('''CREATE TABLE IF NOT EXISTS children
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             chat_id INTEGER,
             name TEXT,
             weekly_allowance REAL,
             balance REAL);''')
conn.commit()

# Het verkrijgen van het Telegram-token uit het bestand
with open('tgtoken.dat', 'r') as token_file:
    token = token_file.read().strip()

# Het maken van een Telegram-botclient
updater = Updater(token, use_context=True)
dispatcher = updater.dispatcher


def update_balance(context):
    # Alle kinderen ophalen uit de database
    cursor = conn.cursor()
    cursor.execute('SELECT id, weekly_allowance, balance FROM children')
    children = cursor.fetchall()

    for child in children:
        child_id, allowance, balance = child

        # Het saldo verhogen met het zakgeldbedrag
        new_balance = balance + allowance

        # Het saldo bijwerken in de database
        cursor.execute('UPDATE children SET balance = ? WHERE id = ?', (new_balance, child_id))
        conn.commit()


def start(update, context):
    chat_id = update.message.chat_id

    # Het controleren of het kind al in de database bestaat
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM children WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()

    if result is None:
        # Het kind toevoegen aan de database als het nog niet bestaat
        cursor.execute('INSERT INTO children (chat_id, name, weekly_allowance, balance) VALUES (?, ?, ?, ?)',
                       (chat_id, '', 0, 0))
        conn.commit()
        context.bot.send_message(chat_id=chat_id, text="Welkom! Voer je naam en zakgeldbedrag in met /configure.")
    else:
        context.bot.send_message(chat_id=chat_id, text="Welkom terug!")


def configure(update, context):
    chat_id = update.message.chat_id
    args = context.args

    # Het controleren of het kind in de database bestaat
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM children WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()

    if result is not None:
        if len(args) == 2:
            name, weekly_allowance = args
            weekly_allowance = float(weekly_allowance)

            # De naam en het zakgeldbedrag bijwerken in de database
            cursor.execute('UPDATE children SET name = ?, weekly_allowance = ? WHERE chat_id = ?',
                           (name, weekly_allowance, chat_id))
            conn.commit()

            context.bot.send_message(chat_id=chat_id, text="Configuratie bijgewerkt!")
        else:
            context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /configure <naam> <zakgeld>")
    else:
        context.bot.send_message(chat_id=chat_id, text="Je bent nog niet geregistreerd. Stuur /start om te beginnen.")


def check_balance(update, context):
    chat_id = update.message.chat_id

    # Het controleren of het kind in de database bestaat
    cursor = conn.cursor()
    cursor.execute('SELECT name, balance FROM children WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()

    if result is not None:
        name, balance = result
        context.bot.send_message(chat_id=chat_id, text=f"{name}, je saldo is €{balance:.2f}.")
    else:
        context.bot.send_message(chat_id=chat_id, text="Je bent nog niet geregistreerd. Stuur /start om te beginnen.")


def main():
    # Het toevoegen van de commando-handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("configure", configure))
    dispatcher.add_handler(CommandHandler("balance", check_balance))

    # Het plannen van de wekelijkse taak op zaterdag om 08:00 uur
    weekly_job = Job(update_balance, interval=604800, first=datetime.time(hour=8))
    updater.job_queue.run_repeating(weekly_job, interval=604800, first=datetime.time(hour=8))

    # Het starten van de bot
    updater.start_polling()


if __name__ == '__main__':
    main()

