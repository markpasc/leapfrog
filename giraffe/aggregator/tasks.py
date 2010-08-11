import logging
from urllib import urlencode
from xml.etree import ElementTree

import httplib2

from celery.decorators import task


@task
def subscribe(feed_url, sub_pk):
    log = logging.getLogger('%s.subscribe' % __name__)

    h = httplib2.Http()
    resp, cont = h.request(feed_url)
    if resp.status != 200:
        # No feed means we can't subscribe to notifications.
        log.warning('HTTP response %d %s trying to fetch feed %s', resp.status, resp.reason, feed_url)
        return

    # Look for the hub link.
    try:
        doc = ElementTree.fromstring(cont)
        hubs = [elem for elem in doc.findall('feed/link') if elem.attrib['rel'] == 'hub']
        hub_url = hubs[0].attrib['href']
    except Exception, exc:
        log.warning('%s trying to find hub in feed %s: %s', type(exc).__name__, feed_url, str(exc))
        return

    # Try to subscribe.
    callback_root = 'http://%s/' % Site.objects.get_current().domain
    callback = urljoin(callback_root, reverse('aggregator-callback'))
    subreq = {
        'hub.callback': callback,
        'hub.mode': 'subscribe',
        'hub.topic': feed_url,
        'hub.verify': 'async',
    }
    h.request(uri=hub_url, method='POST', body=urlencode(subreq),
        headers={'Content-Type': 'application/x-www-form-urlencoded'})

    if resp.status not in (202, 204):
        log.warning('HTTP response %d %s trying to request subscription to feed %s from hub %s',
            resp.status, resp.reason, feed_url, hub_url)

    # Even if the response was correct, we want to mark the subscription as
    # push when the hub verifies the subscription, so we're done.
    return
