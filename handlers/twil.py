from os import getenv
from twisted.internet import defer
from twilio import twiml
from twilio.util import RequestValidator
from .base import CallHandlers
from .errors import CallException

class TwilioHandlers(CallHandlers):

    def __init__(self, db, resource, path_prefix):
        super(TwilioHandlers, self).__init__(db, resource, path_prefix)

        self._site = getenv('HOST', 'http://localhost')

        auth_token = getenv('TWILIO_AUTH_TOKEN')
        if auth_token is None:
            raise Exception('Environment Variable TWILIO_AUTH_TOKEN not defined')
        else:
            self._auth_token = auth_token

    def _validate(self, request):
        full_path = self._site + request.path
        validator = RequestValidator(self._auth_token)
        signature = request.getHeader('X-Twilio-Signature')
        signature = signature if signature else ''
        post_vars = {k:v[0] for k, v in request.args.iteritems()}

        if validator.validate(full_path, post_vars, signature):
            return post_vars
        else:
            raise CallException(400, 'Twilio validation failed')

    def _prompt_response(self, url='/', prompt='', key='#', timeout=30):
        response = twiml.Response()

        with response.gather(action=url, finishOnKey=key, timeout=timeout) as gather:
            gather.say(prompt)

        return response

    def _response(self, text):
        response = twiml.Response()
        response.say(text)
        return response

    def _hangup(self):
        response = twiml.Hangup()
        return response

    def _dial_number(self, url, text, number):
        response = twiml.Response()

        response.say(text)
        response.dial(number, action=url)

        return response

    def _sendsms(self, sms_body, smsto, smsfrom, text):
        response = twiml.Response()
        response.say(text)
        response.sms(sms_body, to=smsto, sender=smsfrom)
        return response

    @defer.inlineCallbacks
    def _get_call_id(self, params):
        call_id = yield self._db.get_twilio_call_id_from_sid(params['CallSid'])
        defer.returnValue(call_id)

    @defer.inlineCallbacks
    def _register_inbound_call(self, params):
        yield self._db.register_twilio_call(params['CallSid'], params['AccountSid'],
                                            params['From'], params['To'], params['CallStatus'])

    @defer.inlineCallbacks
    def _register_call_complete(self, params):
        call_id = yield self._get_call_id(params)
        yield self._db.register_twilio_call_complete(call_id, params['CallStatus'],
                                                     params['CallDuration'])

    @defer.inlineCallbacks
    def _register_outbound_call(self, call_id, params):
        yield self._db.register_twilio_call(params['DialCallSid'], params['AccountSid'],
                                            params['From'], params['To'], params['DialCallStatus'],
                                            params['DialCallDuration'], call_id)
        defer.returnValue(params['DialCallStatus'])
