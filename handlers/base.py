import re
from twisted.internet import defer
from .config import auth_codes

class CallHandlers(object):

    def __init__(self, db, resource, path_prefix):
        self._db = db
        self._register_paths(resource, path_prefix)

    def _register_paths(self, resource, path_prefix):
        methods = [a for a in dir(self) if not a.startswith('_')]

        for name in methods:
            method = getattr(self, name)
            path = path_prefix + name
            resource.register('POST', path, method, self._validate)

    def _prompt_for_user_number(self, prompt):

        response = self._prompt_response('promptforuserpin', prompt)

        return response

    def _prompt_for_contact_name(self, prompt, response=None):
        response = self._prompt_response('matchcontactname', prompt)

        return response

    def _prompt_for_user_pin(self, prompt, response=None):
        response = self._prompt_response('authenticateuser', prompt)

        return response

    @defer.inlineCallbacks
    def handleinboundcall(self, params=None):

        yield self._register_inbound_call(params)
        response = self._prompt_for_user_number("Please enter your mobile number to authenticate")

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def promptforuserpin(self, params=None):

        msisdn = params['Digits']

        call_id = yield self._get_call_id(params)

        if msisdn:
            yield self._db.store_call_auth_msisdn(call_id, msisdn)
            response = self._prompt_for_user_pin("Please enter your PIN number")
        else:
            yield self._db.store_login_attempt(msisdn, call_id,
                                               auth_codes.AUTH_FAIL_INVALID_MSISDN, user_id=None)
            response = self._prompt_for_user_number("The phone number you entered is not valid, \
                                                     please try again")

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def authenticateuser(self, params=None):

        call_id = yield self._get_call_id(params)

        auth_code, user = yield self._perform_user_auth(call_id, params['Digits'])

        if auth_code == auth_codes.AUTH_FAIL_BLACKLIST:
            response = self._response("This login is temporarily blacklisted due \
                                       to failed login attempts. Please try again in 5 minutes")
        elif auth_code == auth_codes.AUTH_FAIL_INVALID_USER or \
             auth_code == auth_codes.AUTH_FAIL_INVALID_PIN:
            response = self._prompt_for_user_number("The phone number or pin you entered is \
                                                     incorrect, please try again. Please \
                                                     enter your number followed by the hash key.")
        elif auth_code == auth_codes.AUTH_SUCCESS:
            welcome_msg = "Welcome {} Please enter the name of the contact followed by \
                           the hash key.".format(user['f_name'])
            response = self._prompt_for_contact_name(welcome_msg)
        else:
            #Unexpected response
            response = self._hangup()

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def matchcontactname(self, params=None):

        regex = self._regex_from_digits(params['Digits'])
        call_id = yield self._get_call_id(params)
        contacts_count = yield self._db.get_contacts_by_regex(call_id, regex)

        if contacts_count == 0:
            prompt = "No contacts found. Please enter the name of the contact \
                      followed by the hash key"
            response = self._prompt_for_contact_name(prompt)
        else:
            response = yield self._listcontacts(call_id)

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def _listcontacts(self, call_id, initial_prompt=''):

        contacts = yield self._db.get_contacts_from_call_id(call_id)

        prompt = initial_prompt
        contact_count = 1
        for contact in contacts:
            resp = "{} {}  ".format(contact_count, contact['full_name'])
            prompt += resp
            contact_count += 1

        response = self._prompt_response('selectcontact', prompt)

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def selectcontact(self, params=None):

        call_id = yield self._get_call_id(params)

        #User pressed only # i.e. play contacts again
        if not params['Digits']:
            response = yield self._listcontacts(call_id)
        #User pressed only * i.g. return to main menu
        elif params['Digits'] == "*":
            response = self._prompt_for_contact_name("Please enter the name of the contact \
                                                      followed by the hash key")
        elif "*" in params['Digits'] or int(params['Digits']) < 1:
            response = yield self._listcontacts(call_id, "Invalid selection, please try again")
        else:
            contact = yield self._db.store_selected_contact(call_id, int(params['Digits']))
            if contact == "F":
                response = yield self._listcontacts(call_id, "Invalid selection, please try \
                                                              again now")
            else:
                response = yield self._listcontactnumbers(call_id)

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def _listcontactnumbers(self, call_id, initial_prompt=''):
        contact = yield self._db.get_selected_contact_from_call_id(call_id)
        if initial_prompt:
            initial_prompt += " "
        text = initial_prompt + "Numbers for {}".format(contact['full_name'])
        for number in contact['numbers']:
            text += "{} {}".format(number['type'], ' '.join(list(number['number'])))
        text += "Press star to select another contact or 0 to text these numbers to your phone"

        response = self._prompt_response('selectnumber', text)

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def selectnumber(self, params=None):

        call_id = yield self._get_call_id(params)

        if params['Digits'] == "*":
            response = self._prompt_for_contact_name("Please enter the name of the \
                                                      contact followed by the hash key")

        elif params['Digits'] == "0":
            contact, sms_body = yield self._get_contact_sms_details(call_id)
            msisdn, long_code = yield self._db.get_call_msisdns(call_id)
            msisdn = strip_plus_sign(msisdn)
            long_code = strip_plus_sign(long_code)
            text = "Sending SMS with numbers for {}".format(contact['full_name'])
            response = self._sendsms(sms_body, msisdn, long_code, text)

        elif params['Digits']:
            selection = int(params['Digits'])
            contact = yield self._db.get_selected_contact_from_call_id(call_id)
            numbers = contact['numbers']
            if selection > len(numbers):
                response = yield self._listcontactnumbers(call_id,
                                                          "Invalid selection, please try again")
            else:
                selection = selection - 1
                selected_number = numbers[selection]
                validated_number = self._validate_number(selected_number['number'])
                if validated_number:
                    print validated_number
                    text = "Dialing {} on {}".format(contact['full_name'],
                                                     selected_number['number'])
                    response = self._dial_number('outboundcallcomplete', text, validated_number)
                else:
                    text = "Cannot dial {}. Please select a different option."\
                           .format(selected_number['number'])
                    response = yield self._listcontactnumbers(call_id, text)

        else:
            response = yield self._listcontactnumbers(call_id,
                                                      "Invalid selection, please try again")

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def outboundcallcomplete(self, params=None):

        call_id = yield self._get_call_id(params)

        status = yield self._register_outbound_call(call_id, params)

        if status == "completed":
            prompt = "Call completed"
        elif status == "busy":
            prompt = "I'm sorry the number you dialled was busy"
        elif status == "no-answer":
            prompt = "I'm sorry there was no answer"
        elif status == "failed":
            prompt == "I'm sorry the call failed"

        response = yield self._listcontactnumbers(call_id, prompt)

        defer.returnValue(str(response))

    @defer.inlineCallbacks
    def inboundcallcomplete(self, params=None):
        yield self._register_call_complete(params)
        defer.returnValue("Success")

    def _validate_number(self, number):
        stripped_number = re.sub(r'\s|-', "", number)
        #Only supports UK numbers
        msisdn = re.compile(r'^44\d{10}$')
        msisdn_with_plus = re.compile(r'^\+44\d{10}$')
        local_num = re.compile(r'^0\d{10}$')
        if msisdn.match(stripped_number):
            ret = "+{}".format(stripped_number)
        elif msisdn_with_plus.match(stripped_number):
            ret = stripped_number
        elif local_num.match(stripped_number):
            ret = "+44{}".format(stripped_number[1:])
        else:
            ret = False
        return ret

    @defer.inlineCallbacks
    def _get_contact_sms_details(self, call_id):
        contact = yield self._db.get_selected_contact_from_call_id(call_id)

        text = "{}: ".format(contact['full_name'])
        for number in contact['numbers']:
            text += "{} - {};".format(number['type'], number['number'])

        defer.returnValue((contact, text))

    @defer.inlineCallbacks
    def _perform_user_auth(self, call_id, digits):
        msisdn, user = yield self._db.get_call_auth_msisdn(call_id)

        blacklisted = yield self._db.check_blacklisting(msisdn)
        print blacklisted
        if blacklisted:
            auth_code = auth_codes.AUTH_FAIL_BLACKLIST
        elif not user:
            auth_code = auth_codes.AUTH_FAIL_INVALID_USER
        else:
            if not digits == user['pin']:
                auth_code = auth_codes.AUTH_FAIL_INVALID_PIN
            else:
                yield self._db.store_login_success(call_id, user['user_id'])
                auth_code = auth_codes.AUTH_SUCCESS

        user_id = user['user_id'] if user else None
        yield self._db.store_login_attempt(msisdn, call_id, auth_code, user_id)

        if auth_code == auth_codes.AUTH_FAIL_INVALID_USER or \
           auth_code == auth_codes.AUTH_FAIL_INVALID_PIN:
            yield self._db.update_blacklisting(msisdn)

        result = (auth_code, user)
        defer.returnValue(result)

    def _regex_from_digits(self, digit_string):
        regex = "^(?i)"
        digits = list(map(str, digit_string))
        digit_to_regex_map = {'2':'[abc]', '3': '[def]', '4': '[ghi]', '5': '[jkl]',
                              '6': '[mno]', '7': '[pqrs]', '8': '[tuv]', '9': '[wxyz]', '0': ' '}
        for digit in digits:
            if digit in digit_to_regex_map:
                regex += digit_to_regex_map[digit]
        return regex

def strip_plus_sign(msisdn):
    return msisdn.lstrip('+')
