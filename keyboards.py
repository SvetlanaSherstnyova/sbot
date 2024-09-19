from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

button_refresh = KeyboardButton(text='ТЫК')
button_settings = KeyboardButton(text='Настройки')
button_faq = KeyboardButton(text='FAQ')
button_operations = KeyboardButton(text='Список операций')
bank_kbd = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('Баланс')).add(button_operations)

def get_settings_kbd(settings_text):
    confirm, hide_kip = list(settings_text)
    confirmation = KeyboardButton(f'Подтверждать перевод: {"ON" if confirm == "+" else "OFF"}')
    anon_kip = KeyboardButton(f'Аноним: {"ON" if hide_kip == "+" else "OFF"}')
    back = KeyboardButton('ТЫК')

    settings = ReplyKeyboardMarkup(resize_keyboard=True).add(anon_kip).add(back)
    return settings

topup = KeyboardButton('Пополнение')
transactions = KeyboardButton('Переводы')
currency = KeyboardButton('Валюта')
code = KeyboardButton('Код пользователя')
chargeback = KeyboardButton('Чарджбэк')
bugs = KeyboardButton('Баги? Идеи?')
back = KeyboardButton('ТЫК')

faq = ReplyKeyboardMarkup(resize_keyboard=True).row(topup, transactions).add(currency, chargeback).row(code, bugs).add(back)

def get_city(city_list):
    city_kbd = ReplyKeyboardMarkup(resize_keyboard=True)
    for city in city_list:
        print(city)
        city_kbd.add(KeyboardButton(city))
    if len(city_list) == 0:
        return ReplyKeyboardRemove()
    return city_kbd

empty = ReplyKeyboardRemove()