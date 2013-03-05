#
# add leapfrog's template loader
#

TEMPLATE_LOADERS = (
    'leapfrog.loaders.Loader',

    # then the default template loaders
    # ...
)


#
# enable the leapfrog app
#

INSTALLED_APPS = (
    # ...
    # all your other apps, plus south and the sentry apps:
    'south',
    'indexer',
    'paging',
    'sentry',
    'sentry.client',

    # and the leapfrog app:
    'leapfrog',
)


#
# include the template context processors
#
TEMPLATE_CONTEXT_PROCESSORS = (
    # include the default django context processors:
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.contrib.messages.context_processors.messages",

    # and add leapfrog's:
    "leapfrog.context_processors.random_rotator",
    "leapfrog.context_processors.typekit_code",
)



#
# web service API settings
#

# create an Application at http://www.typepad.com/account/access/developer and set these settings:
TYPEPAD_APPLICATION = '6p...'  # application ID
TYPEPAD_CONSUMER = ('consumer key', 'secret')
TYPEPAD_ANONYMOUS_ACCESS_TOKEN = ('anonymous access token', 'secret')

# create an app at http://www.flickr.com/services/apps/create/ and set this setting:
FLICKR_KEY = ('key', 'secret')

# create a Facebook app and set this setting:
FACEBOOK_CONSUMER = ('consumer key', 'secret')

# create an app at http://vimeo.com/api/applications and set this setting:
VIMEO_CONSUMER = ('consumer key', 'secret')

# create an app at http://www.tumblr.com/oauth/apps and set this setting:
TUMBLR_CONSUMER = ('oauth consumer key', 'secret')
