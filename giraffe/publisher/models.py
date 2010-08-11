from datetime import datetime
import logging
from random import randint
import sys
from urlparse import urljoin

from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.template.defaultfilters import truncatewords

from giraffe.publisher import tasks


class Asset(models.Model):

    title = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    atom_id = models.CharField(max_length=200, unique=True, blank=True)
    published = models.DateTimeField(default=datetime.now)

    @property
    def preview(self):
        text = self.summary or self.content
        return truncatewords(text, 10)

    def __unicode__(self):
        return self.title or truncatewords(self.summary, 10) or u'No title'

    @models.permalink
    def get_absolute_url(self):
        return ('publisher-asset', (), {'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.atom_id:
            self.atom_id = 'tag:%s,2010:%s' % (Site.objects.get_current().domain, self.slug)
        if self.published is None:
            self.published = datetime.now()
        return super(Asset, self).save(*args, **kwargs)


class Subscription(models.Model):

    callback = models.CharField(max_length=200)
    topic = models.CharField(max_length=200)
    secret = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(User, blank=True, null=True)
    lease_until = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('callback', 'topic'),)


def ping_subscribers(sender, instance, created, **kwargs):
    if not created:
        return

    log = logging.getLogger('.'.join((__name__, 'ping_subscribers')))
    log.debug("Saw a new asset! Looking for subscribers")
    guess_root = 'http://%s/' % Site.objects.get_current().domain
    feed_url = urljoin(guess_root, reverse('publisher-feed'))
    subs = Subscription.objects.filter(topic=feed_url)

    log.debug("Posting %d jobs to tell subscribers about the new asset", len(subs))
    for sub in subs:
        tasks.ping_subscriber.delay(sub.callback, instance.pk, secret=sub.secret)

models.signals.post_save.connect(ping_subscribers, sender=Asset)
