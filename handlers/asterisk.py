import json
from os import getenv
from twisted.internet import defer
from .base import CallHandlers
from .errors import CallException

class AsteriskHandlers(CallHandlers):

    def __init__(self, db, resource, path_prefix):
        super(AsteriskHandlers, self).__init__(db, resource, path_prefix)

        asterisk_http_user = getenv('ASTERISK_HTTP_USER')
        asterisk_http_pass = getenv('ASTERISK_HTTP_PASSWORD')

        if asterisk_http_user is None:
            raise Exception('Environment Variable ASTERISK_HTTP_USER not defined')
        else:
            self._asterisk_http_user = asterisk_http_user

        if asterisk_http_pass is None:
            raise Exception('Environment Variable ASTERISK_HTTP_PASS not defined')
        else:
            self._asterisk_http_pass = asterisk_http_pass

    def _validate(self, request):
        if request.getUser() == self._asterisk_http_user and \
           request.getPassword() == self._asterisk_http_pass:
            #Should add a check for post param inclusion
            post_vars = {k:v[0] for k, v in request.args.iteritems()}
            return post_vars
        else:
            raise CallException(401, 'Unauthorized')

    def _prompt_response(self, url='/', prompt='', key='#', timeout=30):
        response = {'action': url, 'text': prompt, 'timeout':timeout*1000}#milliseconds

        return json.dumps(response)

    def _response(self, text):
        response = {'text': text}

        return json.dumps(response)

    def _hangup(self):
        response = {'hangup': True}

        return json.dumps(response)

    def _sendsms(self, sms_body, smsto, smsfrom, text):
        response = {'text': text}

        #TODO response.sms(sms_body, to=smsto, sender=smsfrom)
        return json.dumps(response)

    @defer.inlineCallbacks
    def _get_call_id(self, params):
        call_id = yield self._db.get_asterisk_call_id_from_uid(params['CallUid'])
        defer.returnValue(call_id)

    @defer.inlineCallbacks
    def _register_inbound_call(self, params):
        yield self._db.register_asterisk_call(params['CallUid'], params['Context'],
                                              params['From'], params['To'])
