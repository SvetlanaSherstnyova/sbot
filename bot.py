import sqlite3
import gspread
import names as meta
import re
import random
import string

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
#from aiogram import Bot, types, Dispatcher, executor

from datetime import datetime

from config import TOKEN
import messages_utopia as msgs
import keyboards as kbds
import names
from telethon import TelegramClient
from config import USER_API_APP_ID, USER_API_APP_HASH
from datetime import datetime, timedelta, timezone


from random import randint

import game as game
#import counter


# Initialize connection to main Google Spreadsheet
gc = gspread.service_account(filename='scibot.json')
#users_sheet = gc.open_by_key('1RKVQQR8htdtvjb3RA3NFTTWgmt8p3LvOZEkKjORp-Fo').worksheet("Users")
#transactions_sheet = gc.open_by_key('1RKVQQR8htdtvjb3RA3NFTTWgmt8p3LvOZEkKjORp-Fo').worksheet("Transactions")

# Initialize connection to SQLite DB
conn = sqlite3.connect("db.sqlite")
#print(sqlite3.version)
c = conn.cursor()


# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

TRANSFER_BLOCKED = False

email_pattern = re.compile('.*@.*\..*..')

pending_email_tgid = set()
tgid_to_email = dict()



# GREETINGS
@dp.message_handler(commands=['start'])
async def greeting_message(message: types.Message):
    await message.answer(msgs.choose_city_text, reply_markup=kbds.empty)



# REGISTRATION (message starts with "*" and then should contain CVV)
@dp.message_handler(regexp='^\*.*')
async def process_start_command(message: types.Message):

    blocked_kips = ("ХУЙ")

    user_id = message.from_user.id
    username = message.from_user.username
    kip = message.text[1:].upper().strip()

    if username is None:
        username = '🥲'

    g = game.get_game(user_id)

    if not user_id in names.admin_ids:
        status = g.register(user_id, username, kip, email=tgid_to_email[user_id], lenmin=names.LEN_MIN, lenmax=names.LEN_MAX)
    else:
        tgid_to_email[user_id] = 'ADMIN'
        status = g.register(user_id, username, kip, email='ADMIN', lenmin=names.LEN_MIN, lenmax=names.LEN_MAX)

    if status == 'already_registered':
        await message.answer(msgs.reg_already_registered, reply_markup=kbds.bank_kbd)
        raise Exception(f"{user_id} (@{username}) is already registered! He tried to do that again with KIP {kip}")
    
    elif status == 'kip_wrong_length':
        await message.answer("Код нужен от 3 до 6 символов!", reply_markup=kbds.bank_kbd)
        raise Exception(f"{user_id} (@{username}) tried bad-lengthened KIP {kip}")
    
    elif status == 'kip_not_available':
        await message.answer(msgs.reg_kip_not_available, reply_markup=kbds.bank_kbd)
        raise Exception(f"{user_id} (@{username}) tried already used KIP {kip}")
    
    elif status == 'kip_blocked':
        await message.answer(msgs.reg_kip_not_available, reply_markup=kbds.bank_kbd)
        raise Exception(f"{user_id} (@{username}) tried blocked KIP {kip}")

    elif status == 'registration_failed':
        await message.answer(msgs.registration_failed)
        raise Exception(f"Unknown error. SQL did not register {user_id} (@{username}) with KIP {kip}")
    
    elif status == 0:
        tgid_to_email.pop(user_id)
        await message.answer(msgs.reg_success, reply_markup=kbds.bank_kbd)
        await bot.send_message(chat_id = user_id, text = f"🆔 {kip}\n🪙 {0} {msgs.currency_name}", reply_markup=kbds.bank_kbd)


# Recieve your TG_ID as a reply
@dp.message_handler(commands=['tgid'])
async def send_welcome(message: types.Message):    
    await message.answer(message.from_user.id)  


@dp.message_handler(text=('Баланс', 'ТЫК'))
async def other(message: types.Message):
    user_id = message.from_user.id
    try:
        g = game.get_game(user_id)
        result = g.get_kip_balance(user_id)
        kip = result[0]
        balance = result[1]
        await bot.send_message(chat_id = user_id, text = f"🆔 {kip}\n🪙 {balance} {msgs.currency_name}", reply_markup=kbds.bank_kbd)
    except:
        await message.answer(msgs.greeting_text)
        await message.answer("Кажется, ты не зарегистрирован :(\nЛови еще раз стартовое сообщение, и подключайся! \nУспехов!")





@dp.message_handler(text='Список операций')
async def google_sync(message: types.Message):
    user_id = message.from_user.id

    g = game.get_game(user_id)
    final_text = g.get_user_transactions(user_id)

    if final_text == "":
        final_text = "Операций с твоим кодом пока не было :("
    await message.answer(final_text, reply_markup=kbds.bank_kbd)

    # Total +
    # Total -
    # Biggest transaction
    # Промокоды?








@dp.message_handler(commands=['give'])
async def give_money(message: types.Message):
    tgid = message.from_user.id
    amount_text = message.text[5:].strip()
    g = game.get_game(tgid)
    if tgid in names.admin_ids:
        try:
            amount = int(amount_text)
        except:
            print('Nope, not a number')
            await message.answer(f"Проверь сообщение. должна быть только сумма", reply_markup=None) 
            return
        g.add_to_all(tgid, amount)
        await message.answer(f"Деньги зачислены на счета игроков, проверяй!", reply_markup=None) 


@dp.message_handler(commands=['rich'])
async def give_money(message: types.Message):
    tgid = message.from_user.id
    amount_text = message.text[5:].strip()
    g = game.get_game(tgid)
    if tgid in names.admin_ids:
        try:
            amount = int(amount_text)
        except:
            print('Nope, not a number')
            await message.answer(f"Проверь сообщение. должна быть только сумма", reply_markup=None) 
            return
        g.update_balance(tgid, amount)
        await message.answer(f"Шикуем!!!", reply_markup=None) 
        await bot.send_message(chat_id = tgid, text = f"🪙 {amount_text} {msgs.currency_name}", reply_markup=kbds.bank_kbd)
        


@dp.message_handler(commands=['g'])
async def admin_input(message: types.Message):
    tgid = message.from_user.id
    if tgid in names.superadmin_ids:
        await message.answer(f"Выбирай игру!", reply_markup=kbds.get_city(game.games_dict.keys())) 

@dp.message_handler(commands=['kill'])
async def admin_input(message: types.Message):
    victim = message.text[5:].upper().strip()
    tgid = message.from_user.id
    g = game.get_game(tgid)
    status = g.delete_user(tgid, victim)
    if tgid in names.admin_ids:
        balance, tg_name, victim_id = status
        await message.answer(f"Охота прошла успешно. Пользователь {victim} (@{tg_name})успешно стёрт с системы. Его {balance} {msgs.currency_name} вернулись к создателю", reply_markup=kbds.bank_kbd) 
        await bot.send_message(chat_id = victim_id, text = f"Ваш аккаунт в Easy был закрыт решением админа.\nЕсли вы считаете, что это было необоснованно, обратитесь к нему", reply_markup=kbds.empty)
        conn.commit()
    else:
        await message.answer('Ну вот и чего ты пытаешься добиться? Лол', reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['go'])
async def admin_input(message: types.Message):
    tg_id = message.from_user.id
    g = game.get_game(tg_id)
    if tg_id in names.admin_ids:
        active = g.toggle_status()
        if not active:
            await message.answer(f"Ну теперь никто не может переводить кроме админов. Да здравствует власть!", reply_markup=kbds.bank_kbd) 
        else:
            await message.answer(f"Ииииии запуск прошел успешно, все ликуют и готовы переводить деньги, уииииии!", reply_markup=kbds.bank_kbd) 
    else:
        await message.answer('Ну вот и чего ты пытаешься добиться? Лол', reply_markup=kbds.bank_kbd)


#ADMIN
@dp.message_handler(commands=['addgame'])
async def admin_input(message: types.Message):
    city_name = message.text[8:].strip()
    city_name = city_name.replace(" ", "_")
    tg_id = message.from_user.id
    if tg_id in names.superadmin_ids:
        game_code = game.add_game(city_name)
        game.city_names[game_code] = city_name
        game.city_name_to_code[city_name] = [game_code]
        await message.answer(f"Игра '{city_name}' создана!\nКод игры:") 
        await message.answer(game_code, reply_markup=kbds.get_city(game.games_dict.keys())) 
    else:
        await message.answer('Прости, ты не суперадмин :(', reply_markup=kbds.bank_kbd)


#ADMIN
@dp.message_handler(commands=['killgame', 'endgame'])
async def admin_input(message: types.Message):
    city_name = message.text[9:].strip()
    city_name = city_name.replace(" ", "_")
    tg_id = message.from_user.id
    if tg_id in names.superadmin_ids:
        if message.text[1] == 'e':
            game.kill_game(city_name)
            await message.answer(f"Ну что же, игра теперь архивирована вместе со всеми участниками :'(", reply_markup=kbds.get_city(game.games_dict.keys())) 
        else:
            game.kill_game(city_name, purge=True)
            await message.answer(f"Ну что же, игра теперь полностью удалена вместе со всеми участниками :'(", reply_markup=kbds.get_city(game.games_dict.keys())) 
    else:
        await message.answer('Прости, ты не суперадмин :(', reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['leave'])
async def admin_input(message: types.Message):
    tg_id = message.from_user.id
    g = game.get_game(tg_id)
    status = g.delete_user(tg_id)
    game.tgid_to_game.pop(tg_id)
    
    if tg_id in names.superadmin_ids:
        await message.answer(f"Теперь ты вне игры. Но зачем? ", reply_markup=kbds.get_city(game.games_dict.keys())) 
    else:
        await message.answer('Прости, ты не суперадмин :(', reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['say'])
async def google_sync(message: types.Message):   
    tg_id = message.from_user.id
    text = message.text
    g = game.get_game(tg_id)
    if tg_id in names.admin_ids:
        game_tgids = g.get_all_tgids()
        for userid in game_tgids:
            await bot.send_message(chat_id = userid[0], text = text[5:], reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['broad'])
async def google_sync(message: types.Message):
    tg_id = message.from_user.id
    text = message.text
    if tg_id in names.superadmin_ids:
        all_tgids = game.get_all_system_users()
        for userid in all_tgids[0]:
            await bot.send_message(chat_id = userid[0], text = text[7:], reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['admin'])
async def google_sync(message: types.Message):
    tg_id = message.from_user.id
    if tg_id in names.superadmin_ids:
        text = message.text[7:].strip().upper()
        g = game.get_game(tg_id)
        user_tgid = g.get_tgid_by_kip(text)
        game.add_admin(user_tgid)
        await message.answer(f'Пользователь {text} успешно назначен админом!', reply_markup=kbds.bank_kbd)
        await bot.send_message(chat_id = user_tgid, text = f'Поздравляю, тебя назначили админом игры!', reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['superadmin'])
async def google_sync(message: types.Message):
    tg_id = message.from_user.id
    if tg_id in names.superadmin_ids:
        text = message.text[12:].strip().upper()
        g = game.get_game(tg_id)
        user_tgid = g.get_tgid_by_kip(text)
        game.add_admin(user_tgid, superadmin=True)
        await message.answer(f'Пользователь {text} успешно назначен суперадмином!', reply_markup=kbds.bank_kbd)
        await bot.send_message(chat_id = user_tgid, text = f'Поздравляю, тебя назначили суперадмином!', reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['noadmin'])
async def google_sync(message: types.Message):
    tg_id = message.from_user.id
    if tg_id in names.superadmin_ids:
        text = message.text[9:].strip().upper()
        g = game.get_game(tg_id)
        user_tgid = g.get_tgid_by_kip(text)
        game.remove_admin(user_tgid)
        await message.answer(f'Пользователь {text} больше не админ!', reply_markup=kbds.bank_kbd)
        await bot.send_message(chat_id = user_tgid, text = f'Теперь ты не админ :(', reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['gen'])
async def google_sync(message: types.Message):
    '''
    Generates one-time code for admin activation
    '''
    tg_id = message.from_user.id
    if tg_id in names.superadmin_ids:
        admin_code = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
        names.admin_codes.add(admin_code)
        await message.answer(admin_code, reply_markup=kbds.bank_kbd)


@dp.message_handler(commands=['supergen'])
async def google_sync(message: types.Message):
    '''
    Generates one-time code for superadmin activation
    '''
    tg_id = message.from_user.id
    if tg_id in names.superadmin_ids:
        superadmin_code = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
        names.superadmin_codes.add(superadmin_code)
        await message.answer(superadmin_code, reply_markup=kbds.bank_kbd)



#TODO
@dp.message_handler(commands=['/listadmins'])
async def google_sync(message: types.Message):
    pass





@dp.message_handler()
async def other(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    username = message.from_user.username
    if user_id in pending_email_tgid:
        if email_pattern.match(text):
            pending_email_tgid.remove(user_id)
            tgid_to_email[user_id] = text
            await bot.send_message(chat_id = user_id, text = msgs.greeting_text, reply_markup=None)
        else:
            await bot.send_message(chat_id = user_id, text = "Неверный формат почты :(", reply_markup=None)
        return
    elif text in game.games_dict.keys() and user_id in names.admin_ids:
        game.tgid_to_game[user_id] = game.games_dict[text]
        #pending_email_tgid.add(user_id)
        await bot.send_message(chat_id = user_id, text = f"Ты выбрал игру: {text}!", reply_markup=kbds.empty)
        await bot.send_message(chat_id = user_id, text = msgs.greeting_text, reply_markup=None)
        return
    elif text in game.city_names.keys():
        game.tgid_to_game[user_id] = game.games_dict[game.city_names[text]]
        await bot.send_message(chat_id = user_id, text = f"Ты выбрал игру {game.city_names[text]}!", reply_markup=kbds.empty)
        if not user_id in names.admin_ids:
            pending_email_tgid.add(user_id)
            await bot.send_message(chat_id = user_id, text = msgs.email_text, reply_markup=None)
        else:
            await bot.send_message(chat_id = user_id, text = msgs.greeting_text, reply_markup=None)
        return
    elif text in names.admin_codes:
        game.add_admin(user_id)
        names.admin_codes.remove(text)
        await message.answer("Код принят. Теперь ты админ!", reply_markup=kbds.bank_kbd) 
        return
    elif text in names.superadmin_codes:
        game.add_admin(user_id, superadmin=True)
        names.superadmin_codes.remove(text)
        await message.answer("Код принят. Теперь ты суперадмин!", reply_markup = kbds.get_city(game.games_dict.keys())) 
        return

    

    solve = False
    try:
        g = game.get_game(user_id)
    except:
        await message.answer("Ты не привязан к игре!\nОтправь мне код игры для начала") 
        return
    
    if g.guess_mode:
        try:
            guess, bid = text.split()
            guess = guess.strip()
            bid = int(bid.strip())
            result = g.add_guess(user_id, guess, bid)
            if result == "OK":
                await message.answer(f"Ставка {bid} на {guess} принята!", reply_markup=kbds.bank_kbd)
            elif result == 'Bidded':
                await message.answer(f"Ты уже сделал ставку! Поменять нельзя, будь внимателен в следующий раз :(", reply_markup=kbds.bank_kbd)
            else:
                await message.answer(f"У тебя не хватает Спасибо :(", reply_markup=kbds.bank_kbd)

        except:
            if not solve:
                if not g.tgid_present(user_id):
                    await message.answer("Для регистрации нужно перед кодом поставить звёздочку.\nНапример, *CODE\nДля переводов звездочка не нужна", reply_markup=kbds.empty) 
                    print(f"Чел тупит при регистрации {text} от {user_id} (@{username})")
                else:
                    await message.answer("Если хочешь сделать ставку, то ты как-то не так написал", reply_markup=kbds.bank_kbd) 
                    print(f"Глупое сообщение {text} от {user_id} (@{username})")
    
    else:
        if not g.active and not user_id in names.admin_ids:
            await message.answer("Переводы в данный момент неактивны :(", reply_markup=kbds.bank_kbd) 
            return
        try:
            num_lines = text.count('\n') + 1
            comment = ""
            if num_lines == 1:
                reciever, amount = text.split()
            elif num_lines >= 2:
                lines = text.split('\n')
                main_info, comment = lines[0], '\n'.join(lines[1:])
                reciever, amount = main_info.split()
                
            else:
                solve = True
                #await message.answer("Проверь формат сообщения, если хочешь сделать перевод:\nКОД СУММА\nили\nКОД СУММА\nКОММЕНТ", reply_markup=kbds.bank_kbd) 
                raise Exception(f"Слишком много строк от {user_id} (@{username}), фе")
            reciever = reciever.upper().strip()
            amount = int(amount)
            kip, balance, username, sender_settings = g.get_full_info_by_tgid(user_id)
            if amount < 0 and user_id not in names.admin_ids:
                await message.answer("Наши благодарности всегда положительные!", reply_markup=kbds.bank_kbd) 
                solve = True
                raise Exception(f"{user_id} (@{username}) tried to transfer negative amount of {amount}")
            if amount > balance and user_id not in names.admin_ids:
                await message.answer(f"Кажется, тебе не хватает {msgs.currency_name} 🥲", reply_markup=kbds.bank_kbd) 
                solve = True
                raise Exception(f"{user_id} (@{username}) tried to transfer too much! balance={balance}, amount={amount}")
            if g.kip_present(reciever) != 1:
                await message.answer("Такого пользователя у нас нет 🥲\nИли он не может получить перевод ", reply_markup=kbds.bank_kbd) 
                solve = True
                raise Exception(f"{user_id} (@{username}) tried to transfer to unknown {reciever}")
            
            #TODO add confirmation message
            g.save_transaction(kip, reciever, amount, comment)
            # COMPLETE TRANSFER
            g.update_balance(user_id, (balance-amount))
            reciever_username, reciever_balance, reciever_tgid, reciever_settings = g.get_full_info_by_kip(reciever)
            g.update_balance(reciever_tgid, (reciever_balance+amount)) 
            g.google_update()
            if comment != "":
                comment = f"💬 {comment}"

            reciever_username_at = f" (@{reciever_username})" if reciever_settings[1] == "-" else ""
            sender_username_at = f" (@{username})" if sender_settings[1] == "-" else ""
            await message.answer(f"Перевод на сумму {amount} {msgs.currency_name} успешно дошел до {reciever}{reciever_username_at}\n{comment}", reply_markup=kbds.bank_kbd) 
            await bot.send_message(chat_id = user_id, text = f"🆔 {kip}\n🪙 {balance - amount} {msgs.currency_name}")

            await bot.send_message(chat_id = reciever_tgid, text = f"Перевод от {kip}{sender_username_at}:\n{amount} {msgs.currency_name}!\n{comment}")
            await bot.send_message(chat_id = reciever_tgid, text = f"🆔 {reciever}\n🪙 {reciever_balance + amount} {msgs.currency_name}")
        except:
            if not solve:
                if not g.tgid_present(user_id):
                    await message.answer("Для регистрации нужно перед кодом поставить звёздочку.\nНапример, *CODE\nДля переводов звездочка не нужна", reply_markup=kbds.empty) 
                    print(f"Чел тупит при регистрации {text} от {user_id} (@{username})")
                else:
                    await message.answer("Если хочешь сделать перевод, то ты как-то не так написал", reply_markup=kbds.bank_kbd) 
                    print(f"Глупое сообщение {text} от {user_id} (@{username})")

if __name__ == '__main__':
    executor.start_polling(dp)
    

