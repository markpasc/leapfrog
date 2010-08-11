from django.http import HttpResponse

from giraffe.aggregator import models


def activity_stream(request):
    return HttpResponse('foo')


def callback(request):
    return HttpResponse('meh')
