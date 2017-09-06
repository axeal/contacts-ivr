
import string
from os import getenv
import gdata.contacts.client
from twisted.internet import defer
from oauth2client.client import OAuth2WebServerFlow

class GoogleHandlers(object):

    def __init__(self, db, resource, path_prefix):
        self._db = db
        self._register_paths(resource, path_prefix)

        site = getenv('HOST', 'http://localhost')
        redirect_uri = site + path_prefix + 'auth_return'

        google_client_id = getenv('GOOGLE_API_CLIENT_ID')
        google_client_secret = getenv('GOOGLE_API_CLIENT_SECRET')

        if google_client_id is None:
            raise Exception('Environment Variable GOOGLE_API_CLIENT_ID not defined')

        if google_client_secret is None:
            raise Exception('Environment Variable GOOGLE_API_CLIENT_SECRET is not defined')

        self._flow = OAuth2WebServerFlow(
            client_id=google_client_id,
            client_secret=google_client_secret,
            scope=['https://www.google.com/m8/feeds',
                   'https://www.googleapis.com/auth/userinfo.email'],
            user_agent='contact-sync',
            redirect_uri=redirect_uri)

    def _auth_uri(self):
        auth_uri = self._flow.step1_get_authorize_url()

        return auth_uri

    def _validate(self, request):
        post_vars = {k:v[0] for k, v in request.args.iteritems()}
        return post_vars

    def _register_paths(self, resource, path_prefix):
        methods = [a for a in dir(self) if not a.startswith('_')]

        for name in methods:
            method = getattr(self, name)
            path = path_prefix + name
            resource.register('GET', path, method, self._validate)

    @defer.inlineCallbacks
    def auth_return(self, code):

        credentials = self._flow.step2_exchange(code)
        contacts = get_contacts(credentials)
        yield self._db.delete_contacts()
        yield self.store_contacts(contacts)
        msg = "{} contacts successfully synced".format(len(contacts))

        defer.returnValue(msg)

    @defer.inlineCallbacks
    def store_contacts(self, contacts):
        for contact in contacts:
            yield self._db.store_contact(contact)

def get_contacts(credentials):

    auth2token = gdata.gauth.OAuth2Token(client_id=credentials.client_id,
                                         client_secret=credentials.client_secret,
                                         scope=['https://www.google.com/m8/feeds'],
                                         access_token=credentials.access_token,
                                         refresh_token=credentials.refresh_token,
                                         user_agent='contact-sync',
                                        )
    client = gdata.contacts.client.ContactsClient()
    auth2token.authorize(client)
    contacts_query = gdata.contacts.client.ContactsQuery(max_results=3000)
    contacts_feed = client.GetContacts(query=contacts_query)

    google_contact_feed = contacts_feed.entry

    contacts = []
    for contact_entry in google_contact_feed:
        google_contact = GoogleContact.parse(contact_entry)
        if google_contact:
            contacts.append(google_contact)

    return contacts

class GoogleContact():
    def __init__(self, first_name, last_name, full_name, google_id):
        self.first_name = first_name
        self.last_name = last_name
        self.full_name = full_name
        self.google_id = google_id

    @classmethod
    def parse(cls, google_contact_entry):
        if google_contact_entry.phone_number and google_contact_entry.name:
            if google_contact_entry.name:
                first_name = google_contact_entry.name.given_name.text[0:50] if \
                    google_contact_entry.name.given_name else ""
                last_name = google_contact_entry.name.family_name.text[0:50] if \
                    google_contact_entry.name.family_name else ""
                full_name = google_contact_entry.name.full_name.text[0:100] if \
                    google_contact_entry.name.full_name else ""
            google_id = string.split(google_contact_entry.id.text, '/')[-1]

            google_contact = GoogleContact(first_name, last_name, full_name, google_id)
            numbers = []
            for number in google_contact_entry.phone_number:
                google_contact_phone_number = GoogleContactPhoneNumber.parse(google_contact, number)
                numbers.append(google_contact_phone_number)

            return {'contact': google_contact, 'numbers': numbers}
        else:
            return None

class GoogleContactPhoneNumber():
    def __init__(self, google_contact, number_type, phone_number):
        self.google_contact = google_contact
        self.number_type = number_type
        self.phone_number = phone_number

    @classmethod
    def parse(cls, google_contact, google_phone_number):
        if google_phone_number.rel:
            number_type = string.split(google_phone_number.rel, '#')[-1]
        elif google_phone_number.label:
            number_type = google_phone_number.label
        else:
            number_type = 'Other'
        contact_phone_number = GoogleContactPhoneNumber(google_contact, number_type,
                                                        google_phone_number.text)

        return contact_phone_number
