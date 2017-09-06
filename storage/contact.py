
from twisted.internet import defer

class ContactStore(object):

    def __init__(self, db):
        self.db = db

    @defer.inlineCallbacks
    def store_contact(self, contact):
        contact_id = yield self.db.runInteraction(self._store_contact, contact)
        defer.returnValue(contact_id)

    def _store_contact(self, txn, contact):

        g_contact = contact['contact']
        cursor = txn.execute('''INSERT INTO contact(user_id, f_name, l_name, full_name, g_id)
                                VALUES(?,?,?,?,?)''', (1, g_contact.first_name, g_contact.last_name,
                                                       g_contact.full_name, g_contact.google_id))
        contact_id = cursor.lastrowid

        for number in contact['numbers']:
            txn.execute('''INSERT INTO contact_phone_number(contact_id, type, number)
                        VALUES(?,?,?)''', (contact_id, number.number_type, number.phone_number))

        return contact_id

    @defer.inlineCallbacks
    def delete_contacts(self):
        yield self.db.runInteraction(self._delete_contacts)

    def _delete_contacts(self, txn):

        txn.execute('DELETE FROM contact_phone_number WHERE 1=1')
        txn.execute('DELETE FROM contact WHERE 1=1')
