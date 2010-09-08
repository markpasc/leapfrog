
from os.path import join, dirname

from django.conf.urls.defaults import *


urlpatterns = patterns('giraffe.aggregator.views',
    url(r'^callback/(?P<sub_pk>\d+)$', 'callback', name='aggregator-callback'),
    url(r'^$', 'activity_stream', name='aggregator-read'),
)

urlpatterns += patterns('',
    url(r'^_ga/static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': join(dirname(__file__), 'static')},
        name='giraffe-static'),
)
