import random

from django.conf import settings


def random_rotation():
    while True:
        yield random.gauss(0, 3)


def random_rotator(request):
    return { 'rot': random_rotation() }


def typekit_code(request):
    try:
        return {'typekit_code': settings.TYPEKIT_CODE}
    except AttributeError:
        return {}
