import random

from django.conf import settings


def random_rotation():
    while True:
        yield random.gauss(0, 3)


def random_rotator(request):
    return { 'rot': random_rotation() }


def typekit_code(request):
    return {
        'typekit_code': getattr(settings, 'TYPEKIT_CODE', None),
        'ganalytics_code': getattr(settings, 'GANALYTICS_CODE', None),
        'zendesk': getattr(settings, 'ZENDESK', None),
        'uservoice': getattr(settings, 'USERVOICE', None),
    }
