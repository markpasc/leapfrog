from os.path import join, dirname

from django.conf.urls.defaults import *
from django.http import HttpResponse


urlpatterns = patterns('rhino.views',
    url(r'^$', 'home', name='home'),
    url(r'^setting/save$', 'save_setting', name='save-setting'),
    url(r'^newitems$', 'new_items', name='new-items'),
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
    url(r'^signin/facebook$', 'rhino.views.signin_facebook', name='signin-facebook'),
    url(r'^complete/facebook$', 'rhino.views.complete_facebook', name='complete-facebook'),
    url(r'^signin/vimeo$', 'rhino.views.signin_vimeo', name='signin-vimeo'),
    url(r'^complete/vimeo$', 'rhino.views.complete_vimeo', name='complete-vimeo'),
    url(r'^signin/tumblr$', 'rhino.views.signin_tumblr', name='signin-tumblr'),
    url(r'^complete/tumblr$', 'rhino.views.complete_tumblr', name='complete-tumblr'),

    url(r'^action/twitter/favorite$', 'rhino.views.favorite_twitter', name='action-twitter-favorite'),
    url(r'^action/twitter/retweet$', 'rhino.views.retweet_twitter', name='action-twitter-retweet'),
    url(r'^action/typepad/favorite$', 'rhino.views.favorite_typepad', name='action-typepad-favorite'),
    url(r'^action/flickr/favorite$', 'rhino.views.favorite_flickr', name='action-flickr-favorite'),
    url(r'^action/tumblr/like$', 'rhino.views.like_tumblr', name='action-tumblr-like'),
    url(r'^action/detach-account$', 'rhino.views.detach_account', name='action-detach-account'),
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
