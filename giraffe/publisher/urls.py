from django.conf.urls.defaults import *


urlpatterns = patterns('giraffe.publisher.views',
    url(r'^$', 'index'),
    url(r'^subscribe$', 'subscribe'),
)
