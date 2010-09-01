from os.path import join, dirname

from django.conf.urls.defaults import *


urlpatterns = patterns('giraffe.friends.federation.views',
    url(r'^\.well-known/federation$', 'federation_document', name='federation_document'),
    url(r'^\.federation/associate$', 'associate_endpoint', name='associate_endpoint'),
)

