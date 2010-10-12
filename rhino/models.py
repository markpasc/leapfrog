from datetime import datetime

from django.db import models
from django.contrib.auth.models import User


class Media(models.Model):

    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    # TODO: change this when we store images locally
    image_url = models.CharField(max_length=255, blank=True)
    embed_code = models.TextField(blank=True)

    def __unicode__(self):
        if self.image_url:
            return unicode("image " + str(self.id) +  " " + self.image_url)
        else:
            return "embed " + str(self.id)


class Person(models.Model):

    user = models.OneToOneField(User, null=True, blank=True)
    display_name = models.CharField(max_length=100)
    avatar = models.ForeignKey(Media, blank=True, null=True)

    def __unicode__(self):
        return unicode(self.display_name)


class Account(models.Model):

    service = models.CharField(max_length=20)
    ident = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    last_updated = models.DateTimeField(default=datetime.now)
    authinfo = models.CharField(max_length=600, blank=True)
    person = models.ForeignKey(Person, related_name='accounts')

    status_background_color = models.CharField(max_length=6, blank=True)
    status_background_image_url = models.CharField(max_length=100, blank=True)
    status_background_tile = models.BooleanField(blank=True)

    def __unicode__(self):
        return u'%s at %s' % (self.display_name, self.service)


class Object(models.Model):

    RENDER_MODE_CHOICES = (
        ('mixed', 'mixed'),
        ('status', 'status'),
        ('image', 'image'),
        ('link', 'link'),
    )

    service = models.CharField(max_length=20, blank=True)
    foreign_id = models.CharField(max_length=255, blank=True)
    public = models.BooleanField(blank=True, default=True)

    title = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True)
    image = models.ForeignKey(Media, null=True, blank=True, related_name="represented_objects")
    author = models.ForeignKey(Account, null=True, blank=True, related_name="authored_objects")

    render_mode = models.CharField(max_length=15, blank=True, default='', choices=RENDER_MODE_CHOICES)

    time = models.DateTimeField(db_index=True)
    permalink_url = models.CharField(max_length=255, blank=True, null=True)

    in_reply_to = models.ForeignKey("Object", related_name='replies', null=True, blank=True)

    def __unicode__(self):
        if self.title:
            return self.title
        return u'%s by %s' % (self.render_mode, unicode(self.author))


class UserStream(models.Model):

    VERB_CHOICES = (
        ('post', 'post'),
        ('share', 'share'),
        ('like', 'like'),
    )

    obj = models.ForeignKey(Object, related_name='stream_items')
    user = models.ForeignKey(User, related_name='stream_items')
    time = models.DateTimeField(default=datetime.now)
    why_account = models.ForeignKey(Account, related_name='stream_items_caused')
    why_verb = models.CharField(max_length=20, choices=VERB_CHOICES)

    # index: (user, when) so we can query WHERE user ORDER BY when

class UserReplyStream(models.Model):

    user = models.ForeignKey(User, related_name='reply_stream_items')
    root = models.ForeignKey(Object, related_name='reply_reply_stream_items')
    root_time = models.DateTimeField()
    reply = models.ForeignKey(Object, related_name='reply_stream_items')
    reply_time = models.DateTimeField()

    # index: (user, root_when, reply_when) so we can query WHERE user, root_when <> ORDER BY reply_when
