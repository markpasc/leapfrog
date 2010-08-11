from django.conf.urls.defaults import *


urlpatterns = patterns('giraffe.aggregator.views',
    url(r'^callback$', 'callback', name='aggregator-callback'),
    url(r'^read$', 'activity_stream', name='aggregator-read'),
)
