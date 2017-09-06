#!/usr/bin/env python

import re
from os import getenv
from os.path import join, dirname
from dotenv import load_dotenv
from twisted.web import server
from twisted.internet import reactor
from twisted.enterprise import adbapi
from storage.call import CallStore
from storage.contact import ContactStore
from handlers.resource import CallResource
from handlers.twil import TwilioHandlers
from handlers.asterisk import AsteriskHandlers
from handlers.google import GoogleHandlers
from util.db import check_database_exists
from util.user import update_user

def configure_database(dbname):
    """Configures the sqlite database and returns a ConnectionPool object.

    Creates database and schema, if it does not already exist, via
    check_database_exists()

    Creates or updates user via update_user()

    Args:
        dbname (string): The name of the sqlite database file
    Returns:
        twisted.enterpise.adbapi.ConnectionPool"""

    check_database_exists(dbname)
    update_user(dbname)

    def _on_db_connect(conn):
        conn.create_function("REGEXP", 2, _regex)

    def _regex(expr, item):
        reg = re.compile(expr)
        return reg.search(item) is not None

    database = adbapi.ConnectionPool("sqlite3", dbname,
                                     check_same_thread=False,
                                     cp_min=1,
                                     cp_max=1,
                                     cp_openfun=_on_db_connect)

    return database

def register_handlers(database, use_asterisk):
    """Creates root resource for the site and attaches request handlers.

    Args:
        database (twisted.enterprise.adbapi.ConnectionPool): sqlite ConnectionPool object
        use_asterisk (bool): Flag to load asterisk handlers or not
    Returns:
        tuple(CallResource, List[CallHandlers]): A tuple, with the root resource
                                                 and registered handlers"""

    root = CallResource()

    contact_store = ContactStore(database)
    call_store = CallStore(database)

    handlers = {}
    handlers['twilio'] = TwilioHandlers(call_store, root, '/twilio/')
    handlers['google'] = GoogleHandlers(contact_store, root, '/google/')
    if use_asterisk:
        handlers['asterisk'] = AsteriskHandlers(call_store, root, '/asterisk/')

    return root, handlers

def load_environment_variables():
    """Loads envionment configured in .env file and returns server config.

    Returns:
        tuple: A tuple with the server port, ip address, the sqlite database name
               and boolean to load asterisk handler"""

    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    port = getenv('PORT', 5080)
    ipaddress = getenv('IP_ADDRESS', '0.0.0.0')
    dbname = getenv('DATABASE', 'ivr.db')
    asterisk = getenv('USE_ASTERISK', 'False')
    use_asterisk = True if asterisk == 'True' else False


    return port, ipaddress, dbname, use_asterisk

def main():

    port, ipaddress, dbname, use_asterisk = load_environment_variables()

    database = configure_database(dbname)
    root, handlers = register_handlers(database, use_asterisk)

    auth_uri = handlers['google']._auth_uri()
    msg = "To sync your contacts visit the following URL in your browser: {}".format(auth_uri)
    print msg

    site = server.Site(root)
    reactor.listenTCP(port, site, interface=ipaddress)
    reactor.run()

if __name__ == '__main__':
    main()
