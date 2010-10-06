from datetime import datetime

from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):

    service = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    who = models.ForeignKey(User)
    last_updated = models.DateTimeField(default=datetime.now)


class Object(models.Model):

    foreign_id = models.CharField(max_length=255, null=True)
    foreign_id_hash = models.CharField(max_length=40, db_index=True, unique=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    summary = models.CharField(max_length=255, blank=True, null=True)
    permalink_url = models.CharField(max_length=255, blank=True, null=True)
    time = models.DateTimeField(db_index=True)

    content = models.TextField(blank=True)

    # ?
    image_url = models.CharField(max_length=255, null=True, blank=True)
    image_width = models.IntegerField(null=True, blank=True)
    image_height = models.IntegerField(null=True, blank=True)

    author = models.ForeignKey('Object', related_name='authored', null=True, blank=True)
    in_reply_to = models.ForeignKey("Object", related_name='replies', null=True, blank=True)
    attachments = models.ManyToManyField("Object", related_name="attached_to", blank=True)
    object_type = models.CharField(max_length=15, blank=True, default='')


class UserStream(models.Model):

    obj = models.ForeignKey(Object, related_name='stream_items')
    who = models.ForeignKey(User, related_name='stream_items')
    when = models.DateTimeField(auto_now_add=True)


class UserReplyStream(models.Model):

    who = models.ForeignKey(User, related_name='reply_stream_items')
    root = models.ForeignKey(Object, related_name='reply_reply_stream_items')
    root_when = models.DateTimeField()
    reply = models.ForeignKey(Object, related_name='reply_stream_items')
    reply_when = models.DateTimeField()

    # index: (who, root_when, reply_when)
