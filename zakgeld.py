import sqlite3
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import datetime
import time
import re

def read_token_from_file():
    # Het lezen van het Telegram-token uit het bestand
    with open('tgtoken.dat', 'r') as token_file:
        token = token_file.read().strip()
    return token

# Het verkrijgen van het Telegram-token uit het bestand
token = read_token_from_file()

# Het maken van een nieuwe updater
updater = Updater(token=token, use_context=True)

# Het maken van een nieuwe dispatcher
dispatcher = updater.dispatcher


def create_database_if_not_exists():
    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het aanmaken van de tabel als deze nog niet bestaat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            weekly_allowance REAL NOT NULL,
            balance REAL NOT NULL
        )
    ''')

    # Het opslaan van de wijzigingen en sluiten van de cursor en de SQLite-verbinding
    conn.commit()
    cursor.close()
    conn.close()

def start(update, context):
    chat_id = update.message.chat_id
    context.bot.send_message(chat_id=chat_id, text="Welkom! Stuur /configure <naam> <zakgeld> om een kind te configureren.")


def configure(update, context):
    chat_id = update.message.chat_id
    args = context.args

    if len(args) == 2:
        name, weekly_allowance = args
        weekly_allowance = float(weekly_allowance)

        # Het maken van een nieuwe SQLite-verbinding en cursor
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Het controleren of de naam al in de database staat
        cursor.execute('SELECT id FROM children WHERE chat_id = ? AND name = ?', (chat_id, name))
        name_result = cursor.fetchone()

        if name_result is not None:
            # De naam overschrijven als deze al bestaat
            cursor.execute('UPDATE children SET weekly_allowance = ? WHERE chat_id = ? AND name = ?',
                        (weekly_allowance, chat_id, name))
            conn.commit()
            context.bot.send_message(chat_id=chat_id, text=f"Configuratie bijgewerkt voor {name}!")
        else:
            # Een nieuw kind toevoegen aan de database
            cursor.execute('INSERT INTO children (chat_id, name, weekly_allowance, balance) VALUES (?, ?, ?, ?)',
                            (chat_id, name, weekly_allowance, 0))
            conn.commit()
            context.bot.send_message(chat_id=chat_id, text="Configuratie toegevoegd!")

        # De cursor en de SQLite-verbinding sluiten
        cursor.close()
        conn.close()
    else:
        context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /configure <naam> <zakgeld>")


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
            name = args[0]
            for child in children:
                if child[0] == name:
                    balance = child[1]
                    context.bot.send_message(chat_id=chat_id, text=f"{name} heeft een saldo van {balance}.")
                    break
            else:
                context.bot.send_message(chat_id=chat_id, text=f"{name} niet gevonden.")
        else:
            for child in children:
                name = child[0]
                balance = child[1]
                context.bot.send_message(chat_id=chat_id, text=f"{name} heeft een saldo van {balance}.")
    else:
        context.bot.send_message(chat_id=chat_id, text="Geen kinderen geconfigureerd.")

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()

def show_configuration(update, context):
    print("debug: function: show_configuration")
    chat_id = update.message.chat_id

    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het controleren of er configuraties zijn voor het huidige chat_id
    cursor.execute('SELECT name, weekly_allowance, balance FROM children WHERE chat_id = ?', (chat_id,))
    configurations = cursor.fetchall()

    if configurations:
        message = "Huidige configuraties:\n"
        for config in configurations:
            # name, weekly_allowance = config
            name, weekly_allowance, balance = config 
            message += f"Naam: {name}, wekelijks: {weekly_allowance}, balance: {balance} \n"

        context.bot.send_message(chat_id=chat_id, text=message)
    else:
        context.bot.send_message(chat_id=chat_id, text="Er zijn geen configuraties gevonden voor dit chat-id.")

    # De cursor en de SQLite-verbinding sluiten
    cursor.close()
    conn.close()


def remove_name(update, context):
    chat_id = update.message.chat_id

    # Het maken van een nieuwe SQLite-verbinding en cursor
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Het controleren of er configuraties zijn voor het huidige chat_id
    cursor.execute('SELECT name FROM children WHERE chat_id = ?', (chat_id,))
    configurations = cursor.fetchall()

    if configurations:
        # Een lijst maken van de namen in de configuraties
        names = [config[0] for config in configurations]

        # Het opzetten van het selectielijstje met de namen
        reply_markup = ReplyKeyboardMarkup(
            [[name] for name in names],
            one_time_keyboard=True,
            resize_keyboard=True
        )

        context.bot.send_message(chat_id=chat_id, text="Selecteer de naam die je wilt verwijderen:", reply_markup=reply_markup)

        # Het instellen van een callback-functie voor het verwerken van de invoer
        def handle_name_input(update, context):
            name = update.message.text

            # Het verwijderen van de naam uit de database
            cursor.execute('DELETE FROM children WHERE chat_id = ? AND name = ?', (chat_id, name))
            conn.commit()

            context.bot.send_message(chat_id=chat_id, text=f"De naam '{name}' is succesvol verwijderd.")

            # De cursor en de SQLite-verbinding sluiten
            cursor.close()
            conn.close()

        # Het toevoegen van de filters en callback-functie aan de dispatcher
        context.dispatcher.add_handler(
            MessageHandler(
                Filters.regex(f"({'|'.join(map(re.escape, names))})"),
                handle_name_input
            )
        )
    else:
        context.bot.send_message(chat_id=chat_id, text="Er zijn geen configuraties gevonden voor dit chat-id.")

        # De cursor en de SQLite-verbinding sluiten
        cursor.close()
        conn.close()


def set_balance(update, context):
    chat_id = update.message.chat_id
    args = context.args

    if len(args) == 2:
        name, balance = args
        balance = float(balance)

        # Het maken van een nieuwe SQLite-verbinding en cursor
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        # Het controleren of het kind in de database bestaat
        cursor.execute('SELECT id FROM children WHERE chat_id = ? AND name = ?', (chat_id, name))
        name_result = cursor.fetchone()

        if name_result is not None:
            # Het saldo bijwerken als het kind in de database staat
            cursor.execute('UPDATE children SET balance = ? WHERE chat_id = ? AND name = ?',
                        (balance, chat_id, name))
            conn.commit()
            context.bot.send_message(chat_id=chat_id, text=f"Saldo bijgewerkt voor {name}!")
        else:
            context.bot.send_message(chat_id=chat_id, text=f"{name} niet gevonden.")

        # De cursor en de SQLite-verbinding sluiten
        cursor.close()
        conn.close()
    else:
        context.bot.send_message(chat_id=chat_id, text="Ongeldige configuratie. Gebruik: /setbalance <naam> <saldo>")

def update_balance(update, context):
    chat_id = update.message.chat_id
    print(chat_id)

    # Lees de toegestane Telegram-ID's uit het bestand "secret.dat"
    allowed_ids = set()
    with open('secret.dat', 'r') as file:
        for line in file:
            allowed_ids.add(int(line.strip()))

    # Controleer of de huidige gebruiker geautoriseerd is
    if chat_id not in allowed_ids:
        context.bot.send_message(chat_id=chat_id, text="Je bent niet geautoriseerd om deze functie uit te voeren.")
        return
    
    context.bot.send_message(chat_id=chat_id, text="Je bent geautoriseerd om deze functie uit te voeren.")
    # Verbinding maken met de database
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()

    # Query om alle items in de database op te halen
    query = "SELECT  name, weekly_allowance, balance, chat_id FROM children"
    cursor.execute(query)
    rows = cursor.fetchall()

    # Loop door de rijen en update de balans
    for row in rows:
        name, weekly_allowance, balance, chat_id = row
        new_balance = balance + weekly_allowance

        # Query om de balans bij te werken voor het huidige item
        update_query = "UPDATE children SET balance = ? WHERE name = ?"
        cursor.execute(update_query, (new_balance, name))

        # Stuur een bericht naar het corresponderende Telegram-ID
        message = f"Beste gebruiker.\n Het zakgeld voor {name} wordt bijgewerkt!\n\nEr wordt {weekly_allowance} euro toegevoegd aan het huidige saldo.\n\nHuidige saldo: {balance} euro.\nNieuwe saldo: {new_balance} euro."
        context.bot.send_message(chat_id=chat_id, text=message)

    # Database wijzigingen opslaan
    connection.commit()

    # Sluit de databaseverbinding
    connection.close()

    # Stuur een bericht naar de huidige chat met de bevestiging
    context.bot.send_message(chat_id=chat_id, text="Het wekelijkse zakgeld is bijgeschreven! Tot volgende week. ")



# Het toevoegen van de commando's aan de dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("configure", configure))
dispatcher.add_handler(CommandHandler("balance", check_balance))
dispatcher.add_handler(CommandHandler("setbalance", set_balance))
dispatcher.add_handler(CommandHandler("showconfig", show_configuration))
dispatcher.add_handler(CommandHandler("removename", remove_name))
dispatcher.add_handler(CommandHandler("updatebalance", update_balance))


# Het maken en starten van de updater
create_database_if_not_exists()
updater.start_polling()

# Het instellen van de update_balance-functie om elke week uitgevoerd te worden
# weekly_interval = timedelta(weeks=1)
# updater.job_queue.run_repeating(update_balance, interval=weekly_interval, first=0)

# Het script draait totdat er op Ctrl+C wordt gedrukt
updater.idle()

def main():
    # Het aanmaken van de database als deze niet bestaat
    create_database_if_not_exists()

    # Het toevoegen van de commando-handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("configure", configure))
    dispatcher.add_handler(CommandHandler("balance", check_balance))
    dispatcher.add_handler(CommandHandler("setbalance", set_balance))
    dispatcher.add_handler(CommandHandler("overview", overview))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("showconfig", show_configuration))
    dispatcher.add_handler(CommandHandler("removename", remove_name))
    dispatcher.add_handler(CommandHandler("updatebalance", update_balance))

    # Het starten van de bot
    updater.start_polling()

    # Het plannen van de wekelijkse taak op zaterdag om 08:00 uur
    while True:
        current_time = datetime.datetime.now().time()
        if current_time.hour == 8 and current_time.minute == 0:
            update_balance(None)
        time.sleep(60)

if __name__ == '__main__':
    #main()
    # Het aanmaken van een nieuwe updater
    updater = Updater(token=token, use_context=True)

    # Het maken van een nieuwe dispatcher
    dispatcher = updater.dispatcher

    # Het aanmaken van de database als deze niet bestaat
    create_database_if_not_exists()

    # Het toevoegen van de commando's aan de dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("configure", configure))
    dispatcher.add_handler(CommandHandler("balance", check_balance))
    dispatcher.add_handler(CommandHandler("setbalance", set_balance))
    dispatcher.add_handler(CommandHandler("showconfig", show_configuration))
    dispatcher.add_handler(CommandHandler("removename", remove_name))
    dispatcher.add_handler(CommandHandler("updatebalance", update_balance))

    # Het starten van de updater
    updater.start_polling()

    # Het script draait totdat er op Ctrl+C wordt gedrukt
    updater.idle()
