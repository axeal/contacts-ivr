import re
import traceback
from itertools import ifilter
from twisted.web.resource import Resource
from twisted.internet import defer
from twisted.web.server import NOT_DONE_YET

from .errors import CallException

class CallResource(Resource):

    _registry = []

    isLeaf = True

    def register(self, method, regex, callback, validation):
        self._registry.append((method, re.compile(regex), callback, validation))

    def _get_callback(self, request):
        #https://github.com/iancmcc/txrestapi/blob/master/txrestapi/resource.py
        filterf = lambda t: t[0] in (request.method, 'ALL')
        for _, regex, callback, val in ifilter(filterf, self._registry):
            result = regex.search(request.path)
            if result:
                return callback, val, result.groupdict()
        return None, None, None

    def render(self, request):
        print request.path
        self._async_render(request)
        return NOT_DONE_YET

    @defer.inlineCallbacks
    def _async_render(self, request):
        try:
            callback, val, _ = self._get_callback(request)
            if callback:
                code = 200
                params = val(request)
                response = yield callback(params)
                self._respond(request, code, response)
                return
            else:
                self._respond(request, 400, "Invalid request")
        except CallException as e:
            self._respond(request, e.code, e.msg)
        except Exception as e:
            print traceback.print_exc()
            self._respond(request, 500, "Internal server error")

    def _respond(self, request, code, response):
        request.setResponseCode(code)
        request.write(response)
        request.finish()
        return NOT_DONE_YET
