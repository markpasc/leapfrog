import httplib2

from celery.decorators import task


@task
def subscribe(feed_url, sub_pk):
    http = httplib2.Http()
    resp, cont = h.request(feed_url)

    # Look for hub link.
    # Try to subscribe.
    # Mark the Subscription as a push sub.
