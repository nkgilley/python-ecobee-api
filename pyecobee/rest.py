import requests, re, json, urllib, ast
from .error import ThrottlingError,RequestError

import platform, pkg_resources
version = "0.2.0"

default_headers = {
    'User-Agent': 'pyechobe-agent/{0} ({1}, {2} {3})'.format(version,
                                                             platform.platform(),
                                                             platform.python_implementation(),
                                                             platform.python_version()),
                  'Content-Type': 'application/json;charset=UTF-8'
}

default_params = {}

class Rest(object):
    def __init__(self, data=None, proxies=None, base_url='https://api.ecobee.com', api_version='1'):
        self.proxies = proxies
        self.api_version = api_version
        self.base_url = base_url.rstrip('/')
        self.data = data

    def _handle_error(self, response):
        # Handle explicit errors.
        if response.status_code == 429:
            raise ThrottlingError()
        # Handle all other errors (400 & 500 level HTTP responses)
        elif response.status_code >= 400:
            raise RequestError(response)
        # Else do nothing if there was no error.

    def _headers(self, given):
        headers = default_headers.copy()
        headers.update(given)
        return headers

    def _params(self, given):
        params = default_params.copy()
        params.update(given)
        return params

    def _get(self, url=None, headers="", params=""):
        response = requests.get(url,
                                headers=headers,
                                params=params,
                                proxies=self.proxies)
        self._handle_error(response)

        return json.loads(response.text, encoding="utf-8")
        #return json.dumps(response.json())

    def _post(self, path, headers, params, data={}):
        response = requests.post(self._compose_url(path),
                                 headers=self._headers(headers),
                                 params=self._params(params),
                                 proxies=self.proxies,
                                 data=json.dumps(data))
        self._handle_error(response)
        return response.json()
