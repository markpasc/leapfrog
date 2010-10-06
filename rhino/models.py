from datetime import datetime

from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):

    service = models.CharField(max_length=20)
    ident = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    who = models.ForeignKey(User)
    last_updated = models.DateTimeField(default=datetime.now)
    authinfo = models.CharField(max_length=600, blank=True)

    def __unicode__(self):
        return u'%s at %s' % (self.display_name, self.service)


class Media(models.Model):

    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    # TODO: change this when we store images locally
    image_url = models.CharField(max_length=255, blank=True)
    embed_code = models.TextField()


class Object(models.Model):

    service = models.CharField(max_length=20, blank=True)
    foreign_id = models.CharField(max_length=255, blank=True)

    name = models.CharField(max_length=255, blank=True, null=True)
    summary = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True)
    permalink_url = models.CharField(max_length=255, blank=True, null=True)
    time = models.DateTimeField(db_index=True)

    media = models.ForeignKey(Media, null=True)

    author = models.ForeignKey('Object', related_name='authored', null=True, blank=True)
    in_reply_to = models.ForeignKey("Object", related_name='replies', null=True, blank=True)
    attachments = models.ManyToManyField("Object", related_name="attached_to", blank=True)
    object_type = models.CharField(max_length=15, blank=True, default='')


class UserStream(models.Model):

    VERB_CHOICES = (
        ('post', 'post'),
        ('share', 'share'),
        ('like', 'like'),
    )

    obj = models.ForeignKey(Object, related_name='stream_items')
    author = models.ForeignKey(User, related_name='stream_items')
    when = models.DateTimeField(auto_now_add=True)
    why_who = models.ForeignKey(User, related_name='stream_items_caused')
    why_verb = models.CharField(max_length=20, choices=VERB_CHOICES)


class UserReplyStream(models.Model):

    who = models.ForeignKey(User, related_name='reply_stream_items')
    root = models.ForeignKey(Object, related_name='reply_reply_stream_items')
    root_when = models.DateTimeField()
    reply = models.ForeignKey(Object, related_name='reply_stream_items')
    reply_when = models.DateTimeField()

    # index: (who, root_when, reply_when)
