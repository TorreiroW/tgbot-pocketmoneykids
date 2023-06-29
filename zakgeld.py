import sqlite3
from telegram.ext import Updater, CommandHandler
import datetime
import time

# Het verkrijgen van het Telegram-token uit het bestand
with open('tgtoken.dat', 'r') as token_file:
    token = token_file.read().strip()

# Het maken van een Telegram-botclient
updater = Updater(token, use_context=True)
dispatcher = updater.dispatcher


def create_database_if_not_exists():
    # Het maken van een SQLite-verbinding
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het uitvoeren van een query om te controleren of de 'children'-tabel al bestaat
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='children'")
    result = cursor.fetchone()

    if result is None:
        # De 'children'-tabel aanmaken als deze nog niet bestaat
        cursor.execute('''
            CREATE TABLE children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name TEXT,
                weekly_allowance REAL,
                balance REAL
            )
        ''')
        conn.commit()

    # De SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def update_balance(context):
    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Alle kinderen ophalen uit de database
    cursor.execute('SELECT id, weekly_allowance, balance FROM children')
    children = cursor.fetchall()

    for child in children:
        child_id, allowance, balance = child

        # Het saldo verhogen met het zakgeldbedrag
        new_balance = balance + allowance

        # Het saldo bijwerken in de database
        cursor.execute('UPDATE children SET balance = ? WHERE id = ?', (new_balance, child_id))
        conn.commit()

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def start(update, context):
    chat_id = update.message.chat_id

    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het controleren of het kind al in de database bestaat
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

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def configure(update, context):
    chat_id = update.message.chat_id
    args = context.args

    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het controleren of het kind in de database bestaat
    cursor.execute('SELECT id FROM children WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()

    if result is not None:
        if len(args) == 2:
            name, weekly_allowance = args
            weekly_allowance = float(weekly_allowance)

            # Het controleren of het kind al geconfigureerd is met dezelfde naam
            cursor.execute('SELECT id FROM children WHERE chat_id = ? AND name = ?', (chat_id, name))
            result = cursor.fetchone()

            if result is None:
                # Het toevoegen van het kind aan de database
                cursor.execute('INSERT INTO children (chat_id, name, weekly_allowance, balance) VALUES (?, ?, ?, ?)',
                            (chat_id, name, weekly_allowance, 0))
                conn.commit()
                context.bot.send_message(chat_id=chat_id, text="Configuratie bijgewerkt!")
            else:
                context.bot.send_message(chat_id=chat_id, text=f"De naam {name} is al geconfigureerd voor dit chat-ID.")
        else:
            context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /configure <naam> <zakgeld>")
    else:
        context.bot.send_message(chat_id=chat_id, text="Je bent nog niet geregistreerd. Stuur /start om te beginnen.")

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def check_balance(update, context):
    chat_id = update.message.chat_id
    args = context.args

    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het controleren of het kind in de database bestaat
    cursor.execute('SELECT name, balance FROM children WHERE chat_id = ?', (chat_id,))
    children = cursor.fetchall()

    if children:
        if len(args) == 1:
            child_name = args[0]
            for child in children:
                name, balance = child
                if name == child_name:
                    context.bot.send_message(chat_id=chat_id, text=f"{name}, je saldo is €{balance:.2f}.")
                    break
            else:
                context.bot.send_message(chat_id=chat_id, text=f"Geen kind gevonden met de naam {child_name}.")
        else:
            context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /balance <naam>")
    else:
        context.bot.send_message(chat_id=chat_id, text="Je bent nog niet geregistreerd. Stuur /start om te beginnen.")

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def set_balance(update, context):
    chat_id = update.message.chat_id
    args = context.args

    if len(args) == 2:
        child_name = args[0]
        new_balance = float(args[1])

        # Het maken van een nieuwe SQLite-verbinding en cursor
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Het bijwerken van het saldo van het kind in de database
        cursor.execute('UPDATE children SET balance = ? WHERE chat_id = ? AND name = ?',
                    (new_balance, chat_id, child_name))
        conn.commit()

        context.bot.send_message(chat_id=chat_id, text=f"Saldo van {child_name} is bijgewerkt naar €{new_balance:.2f}.")

        # De cursor en de SQLite-verbinding sluiten
        cursor.close()
        conn.close()
    else:
        context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /setbalance <naam> <saldo>")


# Het toevoegen van commando-handlers aan de dispatcher
start_handler = CommandHandler('start', start)
configure_handler = CommandHandler('configure', configure)
balance_handler = CommandHandler('balance', check_balance)
set_balance_handler = CommandHandler('setbalance', set_balance)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(configure_handler)
dispatcher.add_handler(balance_handler)
dispatcher.add_handler(set_balance_handler)


def main():
    # Het maken van de database als deze nog niet bestaat
    create_database_if_not_exists()

    # Het starten van de updater
    updater.start_polling()

    # Het periodiek bijwerken van de saldi
    #job_queue = updater.job_queue
    #job_queue.run_repeating(update_balance, interval=timedelta(days=7), first=datetime.time(hour=0, minute=0, second=0))

    # Het stoppen van de updater bij een KeyboardInterrupt
    updater.idle()


if __name__ == '__main__':
    main()
