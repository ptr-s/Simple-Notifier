import telebot
from telebot import types
from datetime import datetime, timedelta
import time
import threading
import random
import copy
import re
from config import *
from enum import Enum
import json

class ChatState(Enum):
    COMMAND = 0 # ожидаем ввода команды
    SET = 1     # ожидаем ввода параметров для команды set
    DEL = 2     # ожидаем ввода параметров для команды del

# global vars
chat_state = ChatState.COMMAND
rems_default = {"Время выпить стакан воды!": ["09:09", "14:12", "18:15"]}
chats = {}
lock_chats = threading.Lock()
thread_map = {}
bot = telebot.TeleBot(API_TOKEN)
parser_time_set = re.compile(r'[^+-]([01]\d:[0-5]\d|2[0-3]:[0-5]\d)')
parser_time_add = re.compile(r'\+([01]\d:[0-5]\d|2[0-3]:[0-5]\d)')
parser_time_del = re.compile(r'-([01]\d:[0-5]\d|2[0-3]:[0-5]\d)')
parser_rem = re.compile(
    r'(?P<command>/set|/del|)\s*(#(?P<num1>\d+))?\s*(?P<times>([+-]?\d\d:\d\d\s*)*)\s*(#(?P<num2>\d+))?\s*(?P<rem>.*)?\s*$')

def start_tread(chat_id):
    print(f"start_tread: chat_id={chat_id}, type={type(chat_id)}")
    thread_map[chat_id] = threading.Thread(target=send_reminders, args=(chat_id,))
    thread_map[chat_id].start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    global chat_state
    chat_state = ChatState.COMMAND
    lock_chats.acquire()
    try:
        print(f"send_welcome: {message.chat.id}: {type(message.chat.id)}")
        if message.chat.id in chats:
            response = "Привет! Я чат бот который напомнит вам о важном"
            response += rems_info(chats[message.chat.id])
        else:
            chats[message.chat.id] = copy.deepcopy(rems_default)
            start_tread(message.chat.id)
            response = "Привет! Я чат бот который будет напоминать пить воду"
            response += rems_info(chats[message.chat.id])
    finally:
        lock_chats.release()

    c_start = types.BotCommand(command='start', description='Начать взаимодействие с ботом')
    c_help = types.BotCommand(command='help', description='Получить помощь по командам')
    c_fact = types.BotCommand(command='fact', description='Рандомный факт о воде')
    c_set = types.BotCommand(command='set', description='Установить напоминание')
    c_del = types.BotCommand(command='del', description='Удалить напоминание')
    c_list = types.BotCommand(command='list', description='Список установленных напоминаний')
    c_def = types.BotCommand(command='default', description='Сбросить настройки')
    bot.set_my_commands([c_start, c_help, c_fact, c_set, c_del, c_list, c_def])
    bot.set_chat_menu_button(message.chat.id, types.MenuButtonCommands('commands'))
    bot.reply_to(message, response)

@bot.message_handler(commands=['help'])
def send_help(message):
    global chat_state
    chat_state = ChatState.COMMAND
    bot.reply_to(message,  "Доступные команды:\n"
        "/start - Начать взаимодействие с ботом\n"
        "/help - Получить помощь по командам\n"
        "/fact - Рандомный факт о воде\n"
        "/set [+-]<HH:MM> ... #<Номер_напоминания> | <Текст_напоминания> - Установить напоминание\n"
        "/del #<Номер_напоминания> | <Текст_напоминания> - Удалить напоминание\n"
        "/list - Список установленных напоминаний\n"
        "/default - Сбросить настройки")

@bot.message_handler(commands=['fact'])
def send_fact(message):
    global chat_state
    chat_state = ChatState.COMMAND
    facts = [
        "**Полярность молекулы воды**: Молекула воды (H₂O) имеет угловую форму и является полярной. Это означает, что один конец молекулы (водородный) имеет небольшой положительный заряд, а другой конец (кислородный) – небольшой отрицательный. Полярность воды играет ключевую роль в ее способности растворять многие вещества и образовывать водородные связи.",
        "**Водородные связи**: Вода обладает уникальными свойствами благодаря водородным связям, которые формируются между молекулами. Эти связи возникают между положительно заряженным водородом одной молекулы и отрицательно заряженным кислородом другой. Водородные связи значительно повышают теплоемкость воды и влияют на ее физические свойства, такие как высокая температура кипения и плавления.",
        "**Аномальная плотность**: Вода имеет максимальную плотность при температуре 4 °C. При дальнейшем охлаждении или нагревании плотность воды уменьшается. Это необычное поведение обусловлено образованием водородных связей, которые заставляют молекулы воды располагаться более свободно в твердом состоянии (льде), что делает лед менее плотным, чем жидкая вода. Именно поэтому лед плавает на поверхности воды.",
        "**Квантовые эффекты**: На молекулярном уровне вода проявляет квантовые эффекты, такие как туннелирование. Это явление может влиять на скорость химических реакций, происходящих в водных растворах, и объясняет некоторые биологические процессы, включая работу ферментов и другие биохимические реакции.",
        "**Изотопы воды**: Вода может содержать разные изотопы водорода (например, дейтерий, D или ^2H, и тритий, T или ^3H), что приводит к образованию тяжелой воды (D₂O). Тяжелая вода имеет различные физические свойства по сравнению с обычной водой, такие как высокая плотность и измененные тепловые характеристики, и используется в ядерной физике, например, в некоторых типах ядерных реакторов."
    ]
    random_fact = random.choice(facts)
    bot.reply_to(message, f"Лови факт о воде {random_fact}")

@bot.message_handler(commands=['set'])
def set_rem(message):
    global chat_state
    rem_dict = parser_rem.match(message.text).groupdict()
    rem_text = rem_dict['rem']
    num = rem_dict['num1']
    rem_number = -1
    if num: rem_number = int(num)
    if rem_number < 0:
        num = rem_dict['num2']
        if num: rem_number = int(num)

    alerts_text = ' ' + rem_dict['times']
    alerts_set = parser_time_set.findall(alerts_text)
    alerts_add = parser_time_add.findall(alerts_text)
    alerts_del = parser_time_del.findall(alerts_text)

    rem_alerts = []
    rem = ""
    lock_chats.acquire()
    try:
        if not message.chat.id in chats:
            chats[message.chat.id] = {}
            start_tread(message.chat.id)

        rems = chats[message.chat.id]
        if 0 <= rem_number < len(rems):
            rem = list(rems)[rem_number]
        elif rem_text in rems:
            rem = rem_text
        elif rem_text:
            rem = rem_text
            rems[rem] = []
        if rem:
            rem_alerts = rems[rem]
            if len(alerts_set) == 0: alerts_set = rem_alerts
            alerts_set += alerts_add
            rem_alerts = [alert for alert in alerts_set if alert not in alerts_del]
            rem_alerts = list(set(rem_alerts))
            rem_alerts.sort()
            rems[rem] = rem_alerts
            chat_state = ChatState.COMMAND
        else:
            chat_state = ChatState.SET
    finally:
        lock_chats.release()
    if chat_state == ChatState.COMMAND:
        bot.reply_to(message, f"Напоминание '{rem}' установленно в {rem_alerts}")
    else:
        bot.reply_to(message, "Введите напоминание в формате: [+-]<HH:MM> ... #<Номер_напоминания> | <Текст_напоминания>")

@bot.message_handler(func=lambda message: chat_state == ChatState.SET)
def set_rem_data(message):
    set_rem(message)

@bot.message_handler(commands=['del'])
def del_rem(message):
    global chat_state
    rem_dict = parser_rem.match(message.text).groupdict()
    rem_text = rem_dict['rem']
    num = rem_dict['num1']
    rem_number = -1
    if num: rem_number = int(num)
    if rem_number < 0:
        num = rem_dict['num2']
        if num: rem_number = int(num)
    lock_chats.acquire()
    try:
        if not message.chat.id in chats:
            chats[message.chat.id] = {}
            start_tread(message.chat.id)

        rem = ""
        rems = chats[message.chat.id]
        if 0 <= rem_number < len(rems):
            rem = list(rems)[rem_number]
        elif rem_text in rems:
            rem = rem_text
        if rem:
            rems.pop(rem, None)
            chat_state = ChatState.COMMAND
            response = f"Напоминание '{rem}' удалено"
        elif not chats[message.chat.id]:
            chat_state = ChatState.COMMAND
            response = "Список напоминаний пуст"
        else:
            chat_state = ChatState.DEL
            response = "Для удаления напоминание введите: #<Номер_напоминания> | <Текст_напоминания>"
    finally:
        lock_chats.release()
    bot.reply_to(message, response)

@bot.message_handler(func=lambda message: chat_state == ChatState.DEL)
def del_rem_data(message):
    del_rem(message)

def rems_info(rems):
    info = ""
    for index, (rem, alerts) in enumerate(rems.items()):
        info += f"\n    #{index} {rem}: {alerts}"
    return info

@bot.message_handler(commands=['list'])
def list_rem(message):
    global chat_state
    chat_state = ChatState.COMMAND
    lock_chats.acquire()
    try:
        print(f"list: chat_id = {message.chat.id}: {type(message.chat.id)}")
        if message.chat.id in chats and chats[message.chat.id]:
            response = "Список напоминаний:"
            response += rems_info(chats[message.chat.id])
        else:
            response = "Список напоминаний пуст"
    finally:
        lock_chats.release()
    bot.reply_to(message, response)

@bot.message_handler(commands=['default'])
def def_rem(message):
    global chat_state
    chat_state = ChatState.COMMAND
    lock_chats.acquire()
    try:
        if not message.chat.id in chats:
            chats[message.chat.id] = {}
            start_tread(message.chat.id)
            print(chats)

        response = "Установлены настройки по умолчанию:"
        chats[message.chat.id] = copy.deepcopy(rems_default)
        response += rems_info(chats[message.chat.id])
    finally:
        lock_chats.release()
    bot.reply_to(message, response)

def send_reminders(chat_id):
    print(f"Thread started for chat: {chat_id}: {type(chat_id)}")
    try:
        old = datetime.now() - timedelta(minutes=1)
        while True:
            now = datetime.now()
            if now.hour != old.hour or now.minute != old.minute:
                old = now
                lock_chats.acquire()
                rems = {}
                try:
                    if chat_id in chats:
                        rems = copy.deepcopy(chats[chat_id])
                    else:
                        print(f"Chat not found {chat_id} or chats[{chat_id}] not dict")
                        print(chats)
                        break
                finally:
                    lock_chats.release()

                now_txt = now.strftime("%H:%M")
                for rem, alerts in rems.items():
                    if now_txt in alerts:
                        bot.send_message(chat_id, rem)

                wait_seconds = 58 - now.second
                if wait_seconds <= 0: wait_seconds = 1
                print(f"thread of chat: {chat_id} sleep {wait_seconds}")
                time.sleep(wait_seconds)
            else:
                time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print(f"except in thread of chat: {chat_id}")
        pass
    finally:
        print(f"Thread finished for chat: {chat_id}")


def data_read(filename: str):
    try:
        with open(filename) as f_in:
            return json.load(f_in)
    except FileNotFoundError:
        print(f"Файл '{filename}' не найден")
    return {}

def data_write(filename: str, data: {}):
    with open(filename, "w", encoding='utf-8') as f_out:
        return json.dump(data, f_out, ensure_ascii=False)

def main():
    # Чтение данных
    data = data_read(DATA_FILE_NAME)
    print(chats)
    for data_id, data_rems in data.items():
        chat_id = int(data_id)
        print(f"data_read: chat_id = {chat_id}: {type(chat_id)}")
        rems = copy.deepcopy(data_rems)
        print(rems)
        chats[chat_id] = rems
        start_tread(chat_id)
    try:
        bot.polling(none_stop=True)
    except (KeyboardInterrupt, SystemExit):
        print("except KeyboardInterrupt, SystemExit")
        pass
    # Сохранение данных
    data_write(DATA_FILE_NAME, chats)

if __name__ == "__main__":
    main()

