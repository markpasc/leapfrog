import random


def random_rotation():
    while True:
        yield random.gauss(0, 3)


def random_rotator(request):
    return { 'rot': random_rotation() }
