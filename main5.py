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

            # De naam en het zakgeldbedrag bijwerken in de database
            cursor.execute('UPDATE children SET name = ?, weekly_allowance = ? WHERE chat_id = ?',
                           (name, weekly_allowance, chat_id))
            conn.commit()

            context.bot.send_message(chat_id=chat_id, text="Configuratie bijgewerkt!")
        else:
            context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /configure <naam> <zakgeld>")
    else:
        context.bot.send_message(chat_id=chat_id, text="Je bent nog niet geregistreerd. Stuur /start om te beginnen.")

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def check_balance(update, context):
    chat_id = update.message.chat_id

    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het controleren of het kind in de database bestaat
    cursor.execute('SELECT name, balance FROM children WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchall()

    if result:
        for child in result:
            name, balance = child
            context.bot.send_message(chat_id=chat_id, text=f"{name}, je saldo is €{balance:.2f}.")
    else:
        context.bot.send_message(chat_id=chat_id, text="Je bent nog niet geregistreerd. Stuur /start om te beginnen.")

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def set_balance(update, context):
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
            child_name, new_balance = args
            new_balance = float(new_balance)

            # Het saldo bijwerken in de database
            cursor.execute('UPDATE children SET balance = ? WHERE chat_id = ? AND name = ?',
                           (new_balance, chat_id, child_name))
            conn.commit()

            context.bot.send_message(chat_id=chat_id, text=f"Zakgeldsaldo voor {child_name} is bijgewerkt!")
        else:
            context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /setbalance <naam> <saldo>")
    else:
        context.bot.send_message(chat_id=chat_id, text="Je bent nog niet geregistreerd. Stuur /start om te beginnen.")

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def main():
    # Het toevoegen van de commando-handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("configure", configure))
    dispatcher.add_handler(CommandHandler("balance", check_balance))
    dispatcher.add_handler(CommandHandler("setbalance", set_balance))

    # Het starten van de bot
    updater.start_polling()

    # Het plannen van de wekelijkse taak op zaterdag om 08:00 uur
    while True:
        current_time = datetime.datetime.now().time()
        if current_time.hour == 8 and current_time.minute == 0:
            update_balance(None)
        time.sleep(60)


if __name__ == '__main__':
    main()

