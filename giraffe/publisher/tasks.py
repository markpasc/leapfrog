from datetime import datetime, timedelta
from random import choice
import string
from urllib import urlencode
import urlparse

from celery.decorators import task


ONE_YEAR_SECONDS = 31556926


@task
def ping():
    return 'pong'


@task
def verify_subscription(callback, mode, topic, lease_seconds=None, secret=None, verify_token=None):
    challenge = ''.join(choice(string.letters + string.digits) for i in range(50))

    query = {
        'hub.mode': mode,
        'hub.topic': topic,
        'hub.challenge': challenge,
    }
    if mode == 'subscribe':
        query['hub.lease_seconds'] = ONE_YEAR_SECONDS if lease_seconds is None else min(ONE_YEAR_SECONDS, lease_seconds)
    if secret is not None and urlparts.scheme == 'https':
        query['hub.secret'] = secret
    if verify_token is not None:
        query['hub.verify_token'] = verify_token
    query_str = urlencode(query)

    urlparts = list(urlparse.urlsplit(callback))
    urlparts[3] = '%s&%s' % (urlparts[3], query_str) if urlparts[3] else query_str
    verify_url = urlparse.urlunsplit(urlparts)

    http = httplib2.Http()
    resp, content = http.request(verify_url)

    if resp.status == 404:
        # The action was refused, so don't do anything.
        return

    success = 200 <= resp.status and resp.status < 300 and verify_token in content

    if success and mode == 'unsubscribe':
        try:
            sub = Subscription.objects.get(callback=callback, topic=topic)
        except Subscription.DoesNotExist:
            pass
        else:
            sub.delete()

    elif success and mode == 'subscribe':
        lease_until = datetime.now() + timedelta(seconds=lease_seconds)
        sub, created = Subscription.objects.get_or_create(callback=callback, topic=topic,
            defaults={'lease_until': lease_until, 'secret': secret})
        if not created:  # we got, so update
            sub.lease_until = lease_until
            sub.secret = secret
            sub.save()
