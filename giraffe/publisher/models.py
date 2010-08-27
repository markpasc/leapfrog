from datetime import datetime
import logging
from random import randint
import sys
from urlparse import urljoin

from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.template.defaultfilters import slugify, striptags, truncatewords
import passogva

import giraffe.friends.models
from giraffe.publisher import tasks


log = logging.getLogger(__name__)


class Asset(models.Model):

    title = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    atom_id = models.CharField(max_length=200, unique=True, blank=True)
    published = models.DateTimeField(default=datetime.now)
    author = models.ForeignKey(giraffe.friends.models.Person, null=True)
    private_to = models.ManyToManyField(giraffe.friends.models.Group)
    in_reply_to = models.ForeignKey('Asset', null=True, blank=True, related_name='replies')
    in_thread_of = models.ForeignKey('Asset', null=True, blank=True, related_name='replies_in_thread')

    @property
    def preview(self):
        text = self.summary or self.content
        return truncatewords(text, 10)

    def __unicode__(self):
        return self.title or truncatewords(self.summary, 10) or u'No title'

    @models.permalink
    def get_absolute_url(self):
        return ('publisher-asset', (), {'slug': self.slug})

    def generate_slug(self):
        other_assets = Asset.objects.exclude(id=self.id) if self.pk else Asset.objects.all()
        log.debug('Generating slug for %r', self)

        slugstem = ''
        if self.title:
            slugstem = slugify(self.title)
            if slugstem:
                log.debug('    Generated slug stem from title')
        if not slugstem and self.summary:
            slugstem = slugify(truncatewords(self.summary, 10))
            if slugstem:
                log.debug('    Generated slug stem from summary')
        if not slugstem and self.content:
            slugstem = slugify(truncatewords(striptags(self.content), 10))
            if slugstem:
                log.debug('    Generated slug stem from content')

        if slugstem:
            log.debug('    Content yielded a slugstem of %r! Building slug from it', slugstem)
            slug = slugstem
            i = 1
            while other_assets.filter(slug=slug).exists():
                slug = '%s-%d' % (slugstem, i)
                i += 1
        else:
            log.debug('    Asset has no content, so generating a random slug')
            len = 14
            while True:
                slug, dashed_slug = passogva.generate_password(len, len)
                len += 1
                if not other_assets.filter(slug=slug).exists():
                    break

        log.debug('    Generated slug %r', slug)
        self.slug = slug

    def save(self, *args, **kwargs):
        if self.published is None:
            self.published = datetime.now()
        if not self.slug:
            self.generate_slug()
        if not self.atom_id:
            self.atom_id = 'tag:%s,2010:%s' % (Site.objects.get_current().domain, self.slug)
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

    # TODO: ping subscribers who are allowed to see the asset
    if instance.private_to.count():
        return

    if getattr(instance, 'imported', False):
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
