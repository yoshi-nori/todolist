from datetime import datetime, timedelta

class CookieMixin:
    _set_cookies = []
    
    def render_to_response(self, content, **response_kwargs):
        response = super().render_to_response(content, **response_kwargs)
        for dic in self._set_cookies:
            response.set_cookie(**dic)
        self._set_cookies = []
        return response

    def get_cookie(self,key):
        return self.request.COOKIES.get(key)

    def set_cookie(self, key, **kwargs):
        if 'max_age' not in kwargs:
            kwargs['max_age'] = 30 * 60  # 30分
        if 'expires' not in kwargs:
            kwargs['expires'] = datetime.strftime(datetime.utcnow() + timedelta(seconds=kwargs['max_age']), "%a, %d-%b-%Y %H:%M:%S GMT")
        self._set_cookies.append(dict(key=key, **kwargs))