from datetime import datetime
from random import randint
import sys

from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.db import models
from django.template.defaultfilters import truncatewords


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
