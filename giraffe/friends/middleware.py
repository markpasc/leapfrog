
from django.conf import settings
from django.utils.importlib import import_module
import logging

class OAuthSessionMiddleware(object):
    def process_request(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", None)
        if auth_header is not None:
            parts = auth_header.split()
            if len(parts) >= 2 and parts[0].lower() == "oauth":
                engine = import_module(settings.SESSION_ENGINE)
                if engine:
                    session_key = parts[1]
                    request.session = engine.SessionStore(session_key)


