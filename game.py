import sqlite3
import gspread
import random
import string
import time
import names
from datetime import datetime

conn = sqlite3.connect("db.sqlite")
c = conn.cursor()

# Initialize connection to main Google Spreadsheet
gc = gspread.service_account(filename='scibot.json')
SHEET = gc.open_by_key('1RKVQQR8htdtvjb3RA3NFTTWgmt8p3LvOZEkKjORp-Fo')
ARCHIVE = gc.open_by_key('1KtIiFbi0oGuRw-t96yLo9kmz1bS-FIoKRGNW9R3YMRY')
tgid_to_game = dict()


#create table with city names and game statuses (active=1, archived=0)
# status = 1 for active games, staus = 0 for archived games
c.execute(""" CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    name TEXT,
                    game_code TEXT,
                    status INTEGER DEFAULT 1
); """)
          

# create table with admins tg_list
# status = 1 for admins, status = 2 for superadmins
c.execute(""" CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    tg_id INTEGER,
                    status INTEGER DEFAULT 1
); """)
currtime = datetime.now()
current_time = currtime.strftime(f"%d.%m.%y %H:%M:%S")

conn.commit()
ws_admins = SHEET.worksheet("admins")



# adds all city names with status=1 to city_names 
c.execute(f"""SELECT name, game_code FROM cities
                WHERE status = 1""")
city_names = {city_tuple[1]: city_tuple[0] for city_tuple in c.fetchall()}
city_name_to_code = {v: k for k,v in city_names.items()}


class Game():
    active = True

    def create_db_users(self,) -> None:
        """creates the table with users and balances for a current city"""
        c.execute(f""" CREATE TABLE IF NOT EXISTS users_{self.city} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    settings TEXT DEFAULT "--",
                    email TEXT,
                    tg_id INTEGER,
                    tg_name TEXT,
                    kip TEXT NOT NULL UNIQUE,
                    balance INTEGER DEFAULT 0
                    ); """)
        conn.commit()


    def create_db_transactions(self,) -> None:
        """creates the table with transactions for a current city"""
        c.execute(f""" CREATE TABLE IF NOT EXISTS trans_{self.city} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        sender TEXT,
                        reciever TEXT,
                        amount INTEGER,
                        comment TEXT
                        ); """)
        conn.commit()


    def create_db(self,) -> None:
        """creates both main databases for a current city"""
        self.create_db_users()
        self.create_db_transactions()


    def remove_db_users(self,) -> None:
        c.execute(f"""DROP TABLE users_{self.city};""")
        conn.commit()


    def remove_db_transactions(self,) -> None:
        c.execute(f"""DROP TABLE trans_{self.city};""")
        conn.commit()






    def empty_db_users(self,) -> None:
        #TODO clear instead of removing
        self.remove_db_users()
        self.create_db_users()


    def empty_db_transactions(self,) -> None:
        #TODO clear instead of removing
        self.remove_db_transactions()
        self.create_db_transactions()


    def __init__(self, city, game_code=None):
        self.city = city
        print(len(city_names))
        if not city in city_names.values():
            self.ws_users = SHEET.add_worksheet(title=f"{city} USER", rows=100, cols=10)
            self.ws_transactions = SHEET.add_worksheet(title=f"{city} CASH", rows=100, cols=10)
        else:
            self.ws_users = SHEET.worksheet(f"{city} USER")
            self.ws_transactions = SHEET.worksheet(f"{city} CASH")
        if game_code is None:
            self.game_code = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
        else:
            self.game_code = game_code
        self.create_db()
    

    def google_update(self,) ->  None:
        """Update both info worksheets for a current city"""
        def worksheet_update(table_name, worksheet):
            c.execute(f"SELECT * FROM {table_name}")
            colnames = []
            for i in c.description:
                colnames.append(i[0])
            main_data = [['-' if cell is None else cell for cell in row] for row in c.fetchall()]
            worksheet.clear()
            worksheet.update("A1", [colnames] + main_data)
        worksheet_update(f"users_{self.city}", self.ws_users)
        worksheet_update(f"trans_{self.city}", self.ws_transactions)

    
########## CHECK FOR PRESENCE ##########

    def tgid_present(self, tgid) -> bool:
        """Check if given tgid is already present in a current city"""
        c.execute(
            f"""SELECT COUNT(1) FROM users_{self.city}
                WHERE tg_id = {tgid}"""
        )
        if c.fetchone()[0] == 1:
            return True
        return False
        

    def kip_present(self, kip) -> bool:
        """Check if given kip is already present in a current city"""
        c.execute(
            f"""SELECT COUNT(1) FROM users_{self.city}
                WHERE kip = '{kip}'"""
        )
        if c.fetchone()[0] == 1:
            return True
        return False
        
########## GET INFO OF A PLAYER ##########

    def get_kip_balance(self, tgid) -> list:
        """Get kip & balance by a given tgid in a current city"""
        c.execute(
            f"""SELECT kip, balance FROM users_{self.city}
                WHERE tg_id = {tgid}"""
        )
        result = c.fetchone()
        return result
    
    
    def get_kip(self, tgid) -> str:
        """Get kip by a given tgid in a current city"""
        c.execute(
        f"""SELECT kip FROM users_{self.city}
            WHERE tg_id={tgid}""")
        return c.fetchone()[0]
    

    def get_tgid_by_kip(self, kip) -> int:
        """Get tgid by a given kip in a current city"""
        c.execute(
        f"""SELECT tg_id FROM users_{self.city}
            WHERE kip='{kip}'""")
        return c.fetchone()[0]
    

    def get_user_transactions(self, tgid) -> str:
        """Get user transactions' infomessage by kip"""
        kip = self.get_kip(tgid)
        c.execute(
            f"""SELECT * FROM trans_{self.city}
                WHERE reciever = '{kip}' OR sender = '{kip}'""")
        transactions = c.fetchall()
    
        final_text = ""
        for trans in transactions:
            _, _, sender, reciever, amount, _ = trans
            space_num = max(0, (6-len(str(amount)))*2+1)
            if sender == kip:
                final_text += f"➖ {amount}{space_num*' '}| {reciever}\n"
                if amount < 0: 
                    final_text = final_text[:-1]+"❗️\n"
            if reciever == kip:
                final_text += f"➕ {amount}{space_num*' '}| {sender}\n"
                if amount < 0: 
                    final_text = final_text[:-1]+"❗️\n"
        return final_text
    

    def get_full_info_by_tgid(self, tgid) -> list:
        """
        By tgid returns kip, balance, tg_name and settings of a player
        """
        c.execute(
            f"""SELECT kip, balance, tg_name, settings FROM users_{self.city}
                WHERE tg_id = {tgid}"""
            )
        return c.fetchone()
    

    def get_full_info_by_kip(self, kip) -> list:
        """
        By kip returns tg_name, balance, tgid and settings of a player
        """
        c.execute(
            f"""SELECT tg_name, balance, tg_id, settings FROM users_{self.city}
                WHERE kip = '{kip}'""")
        return c.fetchone()
    

    def get_all_tgids(self,) -> list[int]:
        """Get all tgids in a current city"""
        c.execute(f"""SELECT tg_id FROM users_{self.city}""")
        tgids = c.fetchall()
        return tgids


########## MANIPULATE DATABASE ##########

    def save_transaction(self, sender, reciever, amount, comment) -> None:
        """Add completed transaction to the db"""
        currtime = datetime.now()
        current_time = currtime.strftime(f"%d.%m.%y %H:%M:%S")
        c.execute(
            f"""INSERT INTO trans_{self.city} (timestamp, sender, reciever, amount, comment)
                VALUES ('{current_time}', '{sender}', '{reciever}', {amount}, '{comment}')"""
        )
        self.google_update()
        conn.commit()
        

    def register(self, user_id, username, kip, email, lenmin, lenmax):
        """
        Completes registration: store tgid, username, kip in the db
        If not possible, returns a string with the problem text
        If okay, returns 0
        """
        blocked_kips = ("ХУЙ")

        if username is None:
            username = '🥲'

        if self.tgid_present(user_id):
            return 'already_registered'
        
        if not lenmin <= len(kip) <= lenmax:
            return 'kip_wrong_length'

        if self.kip_present(kip) or kip in blocked_kips:
            return "kip_not_available"

        if kip in blocked_kips:
            return "kip_blocked"

        # Register user
        currtime = datetime.now()
        current_time = currtime.strftime(f"%d.%m.%y %H:%M:%S")
        c.execute(
            f"""INSERT INTO users_{self.city} (tg_id, tg_name, email, kip, timestamp)
                VALUES ({user_id}, '{username}', '{email}', '{kip}', '{current_time}')"""
        )

        # check to be sure evrth is okay
        c.execute(
            f"""SELECT kip, tg_id, tg_name FROM users_{self.city}
                WHERE kip = '{kip}'"""
        )
        kip, tg_id, tg_name = c.fetchone()
        if not (tg_id == user_id and tg_name == username):
            return "registration_failed"
        
        conn.commit()
        self.google_update()
        return 0
    

    def delete_user(self, admin_tgid, victim=None):
        """
        Deletes user from the db and transfers its balance to the admin
        """
        if victim is not None:
            c.execute(f"""SELECT balance, tg_name, tg_id FROM users_{self.city}
                WHERE kip = '{victim}'""")
            balance, tg_name, victim_id = c.fetchone()
        else:
            c.execute(f"""SELECT balance, tg_name, kip FROM users_{self.city}
                WHERE tg_id = '{admin_tgid}'""")
            balance, tg_name, victim = c.fetchone()
            victim_id = admin_tgid
        c.execute(
        f"""SELECT balance FROM users_{self.city}
            WHERE tg_id = {admin_tgid}""")
        easy_balance = c.fetchone()[0]
        c.execute(
        f"""UPDATE users_{self.city}
            SET balance = {easy_balance + balance}
            WHERE kip = 'ADMIN'"""
        )
        c.execute(
            f"""DELETE FROM users_{self.city}
                WHERE kip = '{victim}'"""
        )
        conn.commit()
        self.google_update()
        return balance, tg_name, victim_id
    

    def update_balance(self, tgid, new_value) -> None:
        """
        Sets balance to a new_value by tgid
        """
        c.execute(
            f"""UPDATE users_{self.city}
                SET balance = {new_value}
                WHERE tg_id = {tgid}"""
            )
        conn.commit()

    
    def add_to_all(self, tgid, amount):
        """
        Changes all balances of players from admin's pocket
        """
        c.execute(
            f"""UPDATE users_{self.city}
                SET balance = balance + {amount}
                WHERE NOT tg_id = {tgid}"""
        )
        c.execute(
            f"""SELECT COUNT(*) from users_{self.city}"""
        )
        row_number = c.fetchone()[0]
        total_money_spent = (row_number - 1) * amount
        c.execute(
            f"""UPDATE users_{self.city}
                SET balance = balance - {total_money_spent}
                WHERE tg_id = {tgid}"""
        )
        conn.commit()
        self.save_transaction(tgid, 'всем!', amount, f'Всего: {total_money_spent}')


########## GAME SETTINGS ##########
        
    def toggle_status(self,) -> None:
        """
        Toggles game status between active and inactive
        """
        self.active = not self.active
        return self.active
    

########## GUESS GAME ##########
    def add_guess(self, tgid, guess, bid) -> str:
        """
        Adds user's guess for the current round
        """
        c.execute(
            f"""SELECT balance from users_{self.city}
                WHERE tg_id = {tgid}"""
        )
        balance = c.fetchone()[0]
        if balance - bid < 0:
            return 'No money'
        c.execute(
            f"""SELECT bid from users_{self.city}
                WHERE tg_id = {tgid}"""
        )
        stored_bid = c.fetchone()[0]
        if stored_bid != 0:
            return 'Bidded'
        c.execute(
            f"""UPDATE users_{self.city}
                SET current_guess = '{guess}'
                WHERE tg_id = {tgid}"""
        )
        c.execute(
            f"""UPDATE users_{self.city}
                SET bid = {bid}
                WHERE tg_id = {tgid}"""
        )
        c.execute(
            f"""UPDATE users_{self.city}
                SET balance = {balance - bid}
                WHERE tg_id = {tgid}"""
        )
        conn.commit()
        return 'OK'


    def check_guesses(self, guess) -> list:
        c.execute(f"""SELECT tg_id, bid, balance FROM users_{self.city}
                       WHERE current_guess = '{guess}'""")
        results = c.fetchall()
        for tgid, bid, balance in results:
            print(tgid, bid, balance)
            c.execute(
            f"""UPDATE users_{self.city}
                SET balance = {int(int(balance) + float(self.multiplier) * int(bid))}
                WHERE tg_id = {tgid}"""
            )
        c.execute(f"""SELECT tg_id, bid FROM users_{self.city}
                       WHERE current_guess != '{guess}'""")
        failed = c.fetchall()
        c.execute(
            f"""UPDATE users_{self.city}
                SET current_guess = ''"""
        )
        c.execute(
            f"""UPDATE users_{self.city}
                SET bid = 0"""
        )
        conn.commit()
        return results, failed

    def toggle_guessing(self,) -> bool:
        self.guess_mode = not self.guess_mode
        return self.guess_mode


    def set_multiplier(self, mult) -> None:
        self.multiplier = float(mult)

print(1)
# part1 = city_names[:20]
# dict(itertools.islice(d.items(), 20))
# part2 = city_names[20:40]
# part3 = city_names[40:]
# part1dict = {
# city_name: Game(city_name, game_code) for game_code, city_name in part1.items()
# }
# print('part1!')
# time.sleep(60)
# print('start part2')
# part2dict = {
# city_name: Game(city_name, game_code) for game_code, city_name in part2.items()
# }
# print('part2!')
# time.sleep(60)
# print('start part3')
# part3dict = {
# city_name: Game(city_name, game_code) for game_code, city_name in part3.items()
# }
# print('part3!')
# games_dict = part1dict | part2dict | part3dict
games_dict = dict()
for game_code, city_name in city_names.items():
    games_dict[city_name] = Game(city_name, game_code)
    print(city_name)
    time.sleep(3)
#games_dict = {
#    city_name: Game(city_name, game_code) for game_code, city_name in city_names.items()
#}
tgid_to_game = dict()
for name in city_names.values():
    c.execute(f"""SELECT tg_id FROM users_{name}""")
    for user_tuple in c.fetchall():
        tgid_to_game[user_tuple[0]] = games_dict[name]


def get_game(tgid) -> Game:
    return tgid_to_game[tgid]


def add_game(city_name):
    """
    Adds a new game to the db and games_dict
    """
    #TODO check for the same name and deal with it somehow
    currtime = datetime.now()
    current_time = currtime.strftime(f"%d.%m.%y %H:%M:%S")
    game = Game(city_name)
    games_dict[city_name] = game
    c.execute(f"""INSERT INTO cities (timestamp, name, game_code)
                VALUES ('{current_time}', '{city_name}', '{game.game_code}')""")
    conn.commit()
    return game.game_code


def update_admin_lists():
    """
    Update admin lists in .names
    Updates google sheet with admin ids
    """
    c.execute(f"""SELECT tg_id FROM admins
        WHERE status > 0""")
    names.admin_ids = {admin_id[0] for admin_id in c.fetchall()}
    if 324772217 not in names.admin_ids:
        names.admin_ids.add(324772217)

    c.execute(f"""SELECT tg_id FROM admins
        WHERE status = 2""")
    names.superadmin_ids = {superadmin_id[0] for superadmin_id in c.fetchall()}
    if 324772217 not in names.superadmin_ids:
        names.superadmin_ids.add(324772217)

    c.execute(f"SELECT * FROM admins")
    colnames = []
    for i in c.description:
        colnames.append(i[0])
    main_data = [['-' if cell is None else cell for cell in row] for row in c.fetchall()]
    ws_admins.update("A1", [colnames] + main_data)
    #print(names.admin_ids, names.superadmin_ids)
    

def add_admin(tgid, superadmin=False) -> None:
    currtime = datetime.now()
    current_time = currtime.strftime(f"%d.%m.%y %H:%M:%S")
    status = 1
    if superadmin:
        status = 2
    c.execute(f"""INSERT INTO admins (timestamp, tg_id, status)
                VALUES ('{current_time}', {tgid}, {status})""")
    conn.commit()
    update_admin_lists()
    

def remove_admin(tgid) -> None:
    c.execute(f"""DELETE FROM admins
                      WHERE tg_id={tgid}""")
    conn.commit()
    update_admin_lists()


def kill_game(city_name, purge=False):
    """
    Deletes a game from the db, games_dict
    If purge=True: total removal of game worksheets
    If purge=False (default): copies game worksheets into archive sheet
    """
    # Remove game from games_dict
    dying_game = games_dict.pop(city_name) 
    # Remove worksheets from the main sheet
    SHEET.del_worksheet(dying_game.ws_users)
    SHEET.del_worksheet(dying_game.ws_transactions)
    # If purge=False: adds worksheets into the archive sheet, sets game status to 0 in the database
    if not purge:
        try:
            dying_game.ws_users = ARCHIVE.add_worksheet(title=f"{city_name} 🪪", rows=100, cols=10)
            dying_game.ws_transactions = ARCHIVE.add_worksheet(title=f"{city_name} 🧾", rows=100, cols=10)
        except:
            print('SAME NAME ADD OPTION LOL')
        dying_game.google_update()
        c.execute(f"""UPDATE cities
                      SET status=0 WHERE name='{city_name}'""") 
        random_threechar = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(3))
        c.execute(f"""UPDATE cities
                      SET name='{city_name}_{random_threechar}' WHERE name='{city_name}'""") 
    else:
        c.execute(f"""DELETE FROM cities
                      WHERE name='{city_name}'""")
    # Remove databases for the game
    c.execute(f"""DROP TABLE users_{city_name};""")
    c.execute(f"""DROP TABLE trans_{city_name};""")

    conn.commit()

    # Remove all players of this game
    global tgid_to_game
    tgid_to_game = {key:val for key, val in tgid_to_game.items() if val != dying_game}



def get_all_system_users() -> list:
    """
    Returns list of all playes in all games
    """

    tgid_list = []
    for game in games_dict.values():
        tgid_list.append(game.get_all_tgids())
    return tgid_list

update_admin_lists()
