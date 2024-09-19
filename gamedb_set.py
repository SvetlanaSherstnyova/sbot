import sqlite3
#from random import randint
#import names as meta

conn = sqlite3.connect("db.sqlite")
c = conn.cursor()

def initial_db_setup():

    #c.execute("""DROP TABLE cities;""")

    """ create the main table: users with their info and all balances in all banks-currencies """
    c.execute(""" CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
    ); """)

    

    
    conn.commit()

initial_db_setup()
conn.close()