from os.path import join, dirname

from django.conf.urls.defaults import *
from django.http import HttpResponse


urlpatterns = patterns('rhino.views',
    url(r'^$', 'home', name='home'),
)

urlpatterns += patterns('',
    url(r'^signin$', 'django.contrib.auth.views.login',
        {'template_name': 'rhino/signin.jj'}, name='signin'),
    url(r'^signout$', 'django.contrib.auth.views.logout',
        {'template_name': 'rhino/signout.jj'}, name='signout'),

    url(r'^signin/twitter$', 'rhino.views.signin_twitter', name='signin-twitter'),
    url(r'^complete/twitter$', 'rhino.views.complete_twitter', name='complete-twitter'),
    url(r'^signin/typepad$', 'rhino.views.signin_typepad', name='signin-typepad'),
    url(r'^complete/typepad$', 'rhino.views.complete_typepad', name='complete-typepad'),
    url(r'^signin/flickr$', 'rhino.views.signin_flickr', name='signin-flickr'),
    url(r'^complete/flickr$', 'rhino.views.complete_flickr', name='complete-flickr'),

    url(r'^action/twitter/favorite$', 'rhino.views.favorite_twitter', name='action-twitter-favorite'),
    url(r'^action/twitter/retweet$', 'rhino.views.retweet_twitter', name='action-twitter-retweet'),
    url(r'^action/typepad/favorite$', 'rhino.views.favorite_typepad', name='action-typepad-favorite'),
    url(r'^action/flickr/favorite$', 'rhino.views.favorite_flickr', name='action-flickr-favorite'),
)

urlpatterns += patterns('',
    url(r'^static/rhino/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': join(dirname(__file__), 'static')},
        name='rhino-static'),
)

urlpatterns += patterns('',
    url(r'^stream\.json$', 'rhino.views.json_stream', name='stream'),
)

urlpatterns += patterns('',
    url(r'^favicon\.ico$', lambda r: HttpResponse('', status=404, content_type='text/plain')),
)
