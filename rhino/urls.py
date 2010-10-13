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
)

urlpatterns += patterns('',
    url(r'^static/rhino/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': join(dirname(__file__), 'static')},
        name='rhino-static'),
)
