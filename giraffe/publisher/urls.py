from django.conf.urls.defaults import *


urlpatterns = patterns('giraffe.publisher.views',
    url(r'^$', 'index', name='publisher-index'),
    url(r'^feed$', 'index', {'template': 'publisher/feed.xml', 'content_type': 'text/plain'}, name='publisher-feed'),
    url(r'^subscribe$', 'subscribe'),
)
