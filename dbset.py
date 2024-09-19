import sqlite3
#from random import randint
#import names as meta

conn = sqlite3.connect("db.sqlite")
c = conn.cursor()

def initial_db_setup():

    c.execute("""DROP TABLE users;""")

    """ create the main table: users with their info and all balances in all banks-currencies """
    c.execute(""" CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    settings TEXT DEFAULT "--",
                    city TEXT,
                    tg_id INTEGER,
                    tg_name TEXT,
                    kip TEXT NOT NULL UNIQUE,
                    balance INTEGER DEFAULT 0
    ); """)

    
    conn.commit()

initial_db_setup()
conn.close()