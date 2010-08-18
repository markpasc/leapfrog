from django.conf.urls.defaults import *


urlpatterns = patterns('giraffe.aggregator.views',
    url(r'^callback/(?P<sub_pk>\d+)$', 'callback', name='aggregator-callback'),
    url(r'^$', 'activity_stream', name='aggregator-read'),
)
