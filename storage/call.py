from handlers.config import auth_codes

from twisted.internet import defer

class CallStore(object):

    def __init__(self, db):
        self.db = db

    @defer.inlineCallbacks
    def store_login_success(self, call_id, user_id):

        sql = 'INSERT INTO authenticated_call (call_id, user_id) VALUES (?,?)'

        yield self.db.runOperation(sql, (call_id, user_id))

    @defer.inlineCallbacks
    def store_login_attempt(self, msisdn, call_id, auth_code, user_id):

        sql = 'INSERT INTO user_auth_attempt (msisdn, call_id, auth_code, user_id) VALUES (?,?,?,?)'

        yield self.db.runOperation(sql, (msisdn, call_id, auth_code, user_id))

    @defer.inlineCallbacks
    def store_call_auth_msisdn(self, call_id, digits):

        sql = 'INSERT OR REPLACE INTO call_auth_msisdn (call_id, msisdn) VALUES (?,?)'

        yield self.db.runOperation(sql, (call_id, digits))

    @defer.inlineCallbacks
    def get_call_msisdns(self, call_id):
        msisdn = None
        long_code = None

        sql = 'SELECT call_from, call_to FROM call WHERE call_id = ?'
        rows = yield self.db.runQuery(sql, (call_id, ))
        if rows:
            row = rows[0]
            msisdn = row[0]
            long_code = row[1]

        defer.returnValue((msisdn, long_code))

    @defer.inlineCallbacks
    def get_call_auth_msisdn(self, call_id):
        msisdn = None
        user = None

        sql = 'SELECT cam.msisdn, u.user_id, u.f_name, u.l_name, u.pin FROM call_auth_msisdn cam LEFT JOIN user u ON cam.msisdn = u.msisdn WHERE call_id = ?'
        rows = yield self.db.runQuery(sql, (call_id, ))
        if rows:
            row = rows[0]
            msisdn = row[0]
            user = {'user_id': row[1],
                    'f_name': row[2],
                    'l_name': row[3],
                    'pin': row[4],
                    'msisdn': row[0]}
        defer.returnValue((msisdn, user))

    @defer.inlineCallbacks
    def check_blacklisting(self, msisdn):

        sql = "SELECT CASE WHEN count(*) > 0 THEN 1 ELSE 0 END FROM user_auth_blacklist WHERE expiry > datetime('now') AND msisdn = ?"

        rows = yield self.db.runQuery(sql, (msisdn, ))
        blacklisted = False if rows[0][0] == 0 else True
        defer.returnValue(blacklisted)

    def _update_blacklisting(self, txn, msisdn):

        sql1 = "SELECT count(*) FROM user_auth_attempt WHERE msisdn = ? AND auth_code IN (?,?) AND ts > datetime('now', '-5 minutes')"
        sql2 = "INSERT INTO user_auth_blacklist (msisdn, expiry) VALUES (?, datetime('now','+10 minutes'))"

        cursor = txn.execute(sql1, (msisdn, auth_codes.AUTH_FAIL_INVALID_PIN, auth_codes.AUTH_FAIL_INVALID_USER))
        row = cursor.fetchone()
        if row[0] >= 3:
            txn.execute(sql2, (msisdn, ))

    @defer.inlineCallbacks
    def update_blacklisting(self, msisdn):

        yield self.db.runInteraction(self._update_blacklisting, msisdn)

    @defer.inlineCallbacks
    def getUserIdFromCallId(self, call_id):

        sql = 'SELECT user_id FROM authenticated_call WHERE call_id = ?'
        rows = yield self.db.runQuery('''SELECT user_id FROM authenticated_call WHERE call_id = ?''', [call_id])
        if rows:
            defer.returnValue(rows[0][0])
        else:
            defer.returnValue(False)

    def _get_contacts_by_regex(self, txn, call_id, regex):

        sql1 = 'DELETE FROM call_matched_contact WHERE call_id = ?'
        sql2 = '''SELECT a.call_id, c.contact_id, c.full_name FROM contact AS c
                  INNER JOIN authenticated_call AS a ON c.user_id = a.user_id
                  WHERE a.call_id = ? AND c.full_name REGEXP ?'''
        sql3 = '''INSERT INTO call_matched_contact (call_id, contact_id) SELECT a.call_id, c.contact_id FROM contact AS c
                  INNER JOIN authenticated_call AS a ON c.user_id = a.user_id
                  WHERE a.call_id = ? AND c.full_name REGEXP ?'''

        txn.execute(sql1, (call_id, ))
        cursor = txn.execute(sql2, (call_id, regex))
        data = cursor.fetchall()
        print "Matched contacts for %s: %s" % (regex, len(data))
        for row in data:
            print row[2]
        cursor = txn.execute(sql3, (call_id, regex))
        return cursor.rowcount

    @defer.inlineCallbacks
    def get_contacts_by_regex(self, call_id, regex):

        yield self.db.runInteraction(self._get_contacts_by_regex, call_id, regex)

    @defer.inlineCallbacks
    def get_contacts_from_call_id(self, call_id):

        sql = '''SELECT c.contact_id, c.f_name, c.l_name, c.full_name FROM contact AS c
                 INNER JOIN call_matched_contact AS cc ON cc.contact_id = c.contact_id
                 INNER JOIN call AS ca ON ca.call_id = cc.call_id
                 WHERE ca.call_id = ?'''

        rows = yield self.db.runQuery(sql, (call_id, ))

        contacts = []

        for row in rows:
            contact = {'contact_id':row[0], 'f_name': row[1], 'l_name': row[2], 'full_name': row[3]}
            contacts.append(contact)

        defer.returnValue(contacts)

    def _store_selected_contact(self, txn, call_id, selection):

        select_sql = 'SELECT contact_id FROM call_matched_contact WHERE call_id = ?'
        insert_sql = 'UPDATE call_matched_contact SET selected = CASE contact_id WHEN ? THEN 1 WHEN NOT ? THEN 0 END WHERE call_id = ?'

        cursor = txn.execute(select_sql, (call_id, ))
        rows = cursor.fetchall()
        if selection > len(rows):
            return "F"
        else:
            contact_id = rows[selection-1][0]
            txn.execute(insert_sql, (contact_id, contact_id, call_id))
            return contact_id

    @defer.inlineCallbacks
    def store_selected_contact(self, call_id, selection):

        contact_id = yield self.db.runInteraction(self._store_selected_contact, call_id, selection)
        defer.returnValue(contact_id)

    @defer.inlineCallbacks
    def get_selected_contact_from_call_id(self, call_id):

        sql = '''SELECT c.contact_id, c.f_name, c.l_name, c.full_name, n.type, n.number FROM contact AS c
                 JOIN call_matched_contact cm ON cm.contact_id = c.contact_id
                 JOIN contact_phone_number n ON n.contact_id = c.contact_id
                 WHERE cm.selected = 1 AND cm.call_id = ?'''

        rows = yield self.db.runQuery(sql, (call_id, ))

        contact = {'numbers': []}
        for row in rows:
            contact['contact_id'] = row[0]
            contact['f_name'] = row[1]
            contact['l_name'] = row[2]
            contact['full_name'] = row[3]
            contact['numbers'].append({'type': row[4], 'number': row[5]})

        defer.returnValue(contact)

    @defer.inlineCallbacks
    def get_twilio_call_id_from_sid(self, call_sid):

        sql = 'SELECT call_id FROM twilio_call WHERE call_sid = ?'

        rows = yield self.db.runQuery(sql, (call_sid, ))
        if rows:
            defer.returnValue(rows[0][0])
        else:
            defer.returnValue(None)

    def _register_twilio_call(self, txn, call_sid, account_sid, call_from, call_to, status, duration, parent_call_id):

        if parent_call_id:
            call_sql = 'INSERT INTO call (call_from, call_to, direction, status, duration, parent_call_id) VALUES (?,?,1,?,?,?)'
            cursor = txn.execute(call_sql, (call_from, call_to, status, duration, parent_call_id))
            call_id = cursor.lastrowid
        else:
            call_sql = 'INSERT INTO call (call_from, call_to, direction, status) VALUES (?,?,0,?)'
            cursor = txn.execute(call_sql, (call_from, call_to, status))
            call_id = cursor.lastrowid

        twilio_sql = 'INSERT INTO twilio_call (call_sid, account_sid, call_id) VALUES (?, ?, ?)'
        txn.execute(twilio_sql, (call_sid, account_sid, call_id))

        print "Call inserted: %s" %(call_id)
        return call_id

    @defer.inlineCallbacks
    def register_twilio_call(self, call_sid, account_sid, call_from, call_to, status, duration=None, parent_call_id=None):
        call_id = yield self.db.runInteraction(self._register_twilio_call, call_sid, account_sid, call_from, call_to, status, duration, parent_call_id)
        defer.returnValue(call_id)

    @defer.inlineCallbacks
    def register_twilio_call_complete(self, call_id, status, duration):

        sql = 'UPDATE call SET status = ?, duration = ? WHERE call_id = ?'

        result = yield self.db.runOperation(sql, (status, duration, call_id))

        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_asterisk_call_id_from_uid(self, call_uid):

        sql = 'SELECT call_id FROM asterisk_call WHERE call_uid = ?'

        rows = yield self.db.runQuery(sql, (call_uid, ))
        if rows:
            defer.returnValue(rows[0][0])
        else:
            defer.returnValue(None)

    def _register_asterisk_call(self, txn, call_uid, context, call_from, call_to):

        call_sql = 'INSERT INTO call (call_from, call_to, direction) VALUES (?,?,0)'
        asterisk_sql = 'INSERT INTO asterisk_call (call_uid, context, call_id) VALUES (?, ?, ?)'

        cursor = txn.execute(call_sql, (call_from, call_to))
        call_id = cursor.lastrowid

        txn.execute(asterisk_sql, (call_uid, context, call_id))

        print "Call inserted: %s" %(call_id)
        return call_id

    @defer.inlineCallbacks
    def register_asterisk_call(self, call_uid, context, call_from, call_to):
        call_id = yield self.db.runInteraction(self._register_asterisk_call, call_uid,
                                               context, call_from, call_to)
        defer.returnValue(call_id)
