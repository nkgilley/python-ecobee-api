from .error import ThrottlingError,RequestError

class Rest(object):
    def __init__(self, data, proxies=None, base_url='https://api.ecobee.com', api_version='1'):
        self.proxies = proxies
        self.api_version = api_version
        self.base_url = base_url.rstrip('/')

    def _compose_url(self, path):
        if (path == "authorize") or (path == "token") :
            return '{0}/{1}'.format(self.base_url, path)
        else:
            return '{0}/{1}/{2}'.format(self.base_url, self.api_version, path)

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

    def _get(self, path, headers, params):
        response = requests.get(self._compose_url(path),
                                headers=self._headers(headers),
                                params=self._params(params),
                                proxies=self.proxies)
        self._handle_error(response)
        return response.json()

    def _post(self, path, headers, params, data={}):
        response = requests.post(self._compose_url(path),
                                 headers=self._headers(headers),
                                 params=self._params(params),
                                 proxies=self.proxies,
                                 data=json.dumps(data))
        self._handle_error(response)
        return response.json()
