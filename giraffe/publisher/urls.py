from os.path import join, dirname

from django.conf.urls.defaults import *


urlpatterns = patterns('giraffe.publisher.views',
    url(r'^$', 'index', name='publisher-index'),
    url(r'^page/(?P<page>\d+)', 'index', name='publisher-index-page'),
    url(r'^feed$', 'index', {'template': 'publisher/feed.xml', 'content_type': 'text/plain'}, name='publisher-feed'),
    url(r'^asset/(?P<slug>[\w-]+)$', 'asset', name='publisher-asset'),

    url(r'^subscribe$', 'subscribe', name='publisher-subscribe'),
)

urlpatterns += patterns('',
    url(r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': join(dirname(__file__), 'static')},
        name='publisher-static'),
)
