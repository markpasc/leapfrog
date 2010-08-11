from datetime import datetime, timedelta
import hmac
from random import choice
import logging
import string
from urllib import urlencode
import urlparse

from celery.decorators import task
from django.template.loader import render_to_string
import httplib2


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

    success = 200 <= resp.status and resp.status < 300 and challenge == content

    from giraffe.publisher import models

    if success and mode == 'unsubscribe':
        try:
            sub = models.Subscription.objects.get(callback=callback, topic=topic)
        except models.Subscription.DoesNotExist:
            pass
        else:
            sub.delete()

    elif success and mode == 'subscribe':
        lease_until = datetime.now() + timedelta(seconds=lease_seconds or ONE_YEAR_SECONDS)
        sub, created = models.Subscription.objects.get_or_create(callback=callback, topic=topic,
            defaults={'lease_until': lease_until, 'secret': secret})
        if not created:  # we got, so update
            sub.lease_until = lease_until
            sub.secret = secret
            sub.save()

    else:
        logging.error("Either not successful or you were wrong in mode")


@task
def ping_subscriber(callback, asset_pk, secret=None):
    log = logging.getLogger('.'.join((__name__, 'ping_subscriber')))

    from giraffe.publisher.models import Asset

    log.debug('Pinging subscriber %r about asset %r', callback, asset_pk)
    try:
        asset = Asset.objects.get(pk=asset_pk)
    except Asset.DoesNotExist:
        # OH WELL
        log.debug("Oops, no such asset %r; guess we won't ping about it", asset_pk)
        return

    feed = render_to_string('publisher/feed.xml', {
        'assets': [asset],
    })
    headers = {'Content-Type': 'application/atom+xml'}

    if secret is not None:
        headers['X-Hub-Signature'] = hmac.new(secret, feed).hexdigest()

    http = httplib2.Http()
    log.debug("Pinging %r with %d bytes of made-up feed", callback, len(feed))
    resp, cont = http.request(uri=callback, method='POST', body=feed, headers=headers)

    if 200 <= resp.status and resp.status < 300:
        # Sweet, that worked.
        log.debug("Yay, got response %d telling %r about asset %d!", resp.status, callback, asset_pk)
        return

    # TODO: try again?
    log.warning("Unexpected response notifying subscriber %r about asset %d: %d %s", callback, asset_pk, resp.status, resp.reason)
    return
