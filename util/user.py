
from os import getenv
import sqlite3

def update_user(dbname):
    """Create or update user based on user details in environment variables."""

    f_name, l_name, msisdn, pin = get_user_details()

    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    sql = 'INSERT OR REPLACE INTO user (user_id, f_name, l_name, msisdn, pin) VALUES (?,?,?,?,?)'
    cursor.execute(sql, (1, f_name, l_name, msisdn, pin))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_details():
    """Get user details from environment variables."""

    first_name = getenv('USER_FIRST_NAME', 'User')
    last_name = getenv('USER_LAST_NAME', '')
    msisdn = getenv('USER_PHONE_NUMBER')
    pin = getenv('USER_PIN_NUMBER')

    if msisdn is None:
        raise Exception('Environment Variable USER_PHONE_NUMBER not defined')

    if msisdn is None:
        raise Exception('Environment Variable USER_PIN_NUMBER not defined')

    return first_name, last_name, msisdn, pin
