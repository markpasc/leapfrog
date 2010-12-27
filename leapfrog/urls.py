from os.path import join, dirname

from django.conf.urls.defaults import *
from django.http import HttpResponse


urlpatterns = patterns('leapfrog.views',
    url(r'^$', 'home', name='home'),
    url(r'^mobile$', 'mobile_home', name='mobile-home'),
    url(r'^setting/save$', 'save_setting', name='save-setting'),
    url(r'^newitems$', 'new_items', name='new-items'),
)

urlpatterns += patterns('',
    url(r'^signin$', 'django.contrib.auth.views.login',
        {'template_name': 'leapfrog/signin.jj'}, name='signin'),
    url(r'^signout$', 'django.contrib.auth.views.logout',
        {'template_name': 'leapfrog/signout.jj'}, name='signout'),

    url(r'^signin/twitter$', 'leapfrog.views.signin_twitter', name='signin-twitter'),
    url(r'^complete/twitter$', 'leapfrog.views.complete_twitter', name='complete-twitter'),
    url(r'^signin/typepad$', 'leapfrog.views.signin_typepad', name='signin-typepad'),
    url(r'^complete/typepad$', 'leapfrog.views.complete_typepad', name='complete-typepad'),
    url(r'^signin/flickr$', 'leapfrog.views.signin_flickr', name='signin-flickr'),
    url(r'^complete/flickr$', 'leapfrog.views.complete_flickr', name='complete-flickr'),
    url(r'^signin/facebook$', 'leapfrog.views.signin_facebook', name='signin-facebook'),
    url(r'^complete/facebook$', 'leapfrog.views.complete_facebook', name='complete-facebook'),
    url(r'^signin/vimeo$', 'leapfrog.views.signin_vimeo', name='signin-vimeo'),
    url(r'^complete/vimeo$', 'leapfrog.views.complete_vimeo', name='complete-vimeo'),
    url(r'^signin/tumblr$', 'leapfrog.views.signin_tumblr', name='signin-tumblr'),
    url(r'^complete/tumblr$', 'leapfrog.views.complete_tumblr', name='complete-tumblr'),

    url(r'^action/twitter/favorite$', 'leapfrog.views.favorite_twitter', name='action-twitter-favorite'),
    url(r'^action/twitter/retweet$', 'leapfrog.views.retweet_twitter', name='action-twitter-retweet'),
    url(r'^action/typepad/favorite$', 'leapfrog.views.favorite_typepad', name='action-typepad-favorite'),
    url(r'^action/flickr/favorite$', 'leapfrog.views.favorite_flickr', name='action-flickr-favorite'),
    url(r'^action/tumblr/like$', 'leapfrog.views.like_tumblr', name='action-tumblr-like'),
    url(r'^action/detach-account$', 'leapfrog.views.detach_account', name='action-detach-account'),
)

urlpatterns += patterns('',
    url(r'^static/leapfrog/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': join(dirname(__file__), 'static')},
        name='leapfrog-static'),
)

urlpatterns += patterns('',
    url(r'^stream\.json$', 'leapfrog.views.json_stream', name='stream'),
)
