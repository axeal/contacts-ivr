
import os.path
import sqlite3

def check_database_exists(dbname):
    """Check if the sqlite database file exists, and initiliase database if not."""
    if not os.path.isfile(dbname):
        create_ivr_database(dbname)

def create_ivr_database(dbname):
    """Create sqlite database schema from sql script file."""
    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    parent_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sql_script_path = os.path.join(parent_directory, 'db.sql')
    sql_script_file = open(sql_script_path, 'r')
    sql = sql_script_file.read()
    sql_script_file.close()
    cursor.executescript(sql)
    cursor.close()
    conn.close()
