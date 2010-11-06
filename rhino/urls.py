from os.path import join, dirname

from django.conf.urls.defaults import *


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
)

urlpatterns += patterns('',
    url(r'^\w+$', 'rhino.views.redirect_home'),
    url(r'^\w+/activity', 'rhino.views.redirect_home'),
)

urlpatterns += patterns('',
    url(r'^static/rhino/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': join(dirname(__file__), 'static')},
        name='rhino-static'),
)

urlpatterns += patterns('',
    url(r'^stream\.json$', 'rhino.views.json_stream'),
)

