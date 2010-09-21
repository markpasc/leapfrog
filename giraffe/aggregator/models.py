import hashlib

from django.db import models

from giraffe.aggregator import tasks


class Subscription(models.Model):

    display_name = models.CharField(max_length=75, null=True, blank=True)
    topic_url = models.CharField(max_length=255)
    topic_url_hash = models.CharField(max_length=40, db_index=True, blank=True, unique=True)
    user = models.ForeignKey('auth.User', null=True, blank=True, related_name="aggregator_subscriptions")
    mode = models.CharField(max_length=20, choices=(
        ('poll', 'Poll'),
        ('push', 'Push'),
    ), default='poll')

    @classmethod
    def lookup_by_topic_url(cls, url):
        hash = sha1_hex(url)
        return cls.objects.get(topic_url_hash=hash)

    def save(self):
        self.topic_url_hash = sha1_hex(self.topic_url)
        super(Subscription, self).save()

    def __unicode__(self):
        return self.topic_url


def subscribe(sender, instance, created, **kwargs):
    if not created:
        return

    tasks.subscribe.delay(instance.topic_url, instance.pk)

models.signals.post_save.connect(subscribe, sender=Subscription)


class Object(models.Model):

    foreign_id = models.CharField(max_length=255, null=True)
    foreign_id_hash = models.CharField(max_length=40, db_index=True, unique=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    summary = models.CharField(max_length=255, blank=True, null=True)
    permalink_url = models.CharField(max_length=255, blank=True, null=True)
    time = models.DateTimeField(db_index=True)

    image_url = models.CharField(max_length=255, null=True, blank=True)
    image_width = models.IntegerField(null=True, blank=True)
    image_height = models.IntegerField(null=True, blank=True)

    author = models.ForeignKey('Object', related_name='authored', null=True, blank=True)
    in_reply_to = models.ForeignKey("Object", related_name='replies', null=True, blank=True)
    attachments = models.ManyToManyField("Object", related_name="attached_to", blank=True)
    object_type = models.CharField(max_length=15, blank=True, default='')

    @classmethod
    def lookup_by_foreign_id(cls, foreign_id):
        hash = sha1_hex(foreign_id)
        return cls.objects.get(foreign_id_hash=hash)

    def save(self):
        if self.foreign_id:
            self.foreign_id_hash = sha1_hex(self.foreign_id)
        else:
            self.foreign_id_hash = None
        if self.time is None:
            self.time = datetime.now()
        super(Object, self).save()

    def __unicode__(self):
        if self.foreign_id is not None:
            if self.name is not None:
                return self.foreign_id+" ("+self.name+")"
            else:
                return self.foreign_id
        else:
            if self.name is not None:
                return "Anon ("+self.name+")"
            else:
                return "Anon"


class Activity(models.Model):

    verb = models.CharField(max_length=15)
    actor = models.ForeignKey("Object", related_name="activities_with_actor", null=True, blank=True)
    object = models.ForeignKey("Object", related_name="activities_with_object", null=True, blank=True)
    target = models.ForeignKey("Object", related_name="activities_with_target", null=True, blank=True)
    time = models.DateTimeField(db_index=True)
    subscription = models.ForeignKey("Subscription", related_name="activities")
    user = models.ForeignKey("auth.User", null=True, blank=True, related_name="activities")
    uniq_hash = models.CharField(max_length=40, db_index=True, unique=True, blank=True)

    @classmethod
    def lookup_by_as_activity(cls, as_activity):
        parts = []
        verb = as_activity.verb
        if verb is not None:
            verb = verb.replace("http://activitystrea.ms/schema/1.0/", "", 1)

        parts.append(verb)
        parts.append(as_activity.time.isoformat())
        if as_activity.actor is not None:
            parts.append(as_activity.actor.id)
        else:
            parts.append("")

        if as_activity.object is not None:
            parts.append(as_activity.object.id)
        else:
            parts.append("")

        if as_activity.target is not None:
            parts.append(as_activity.target.id)
        else:
            parts.append("")

        print "Base string for lookup is "+(" ".join(parts))

        hash = sha1_hex("\t".join(parts))

        print "Hash for lookup is "+hash

        return cls.objects.get(uniq_hash=hash)

    def save(self):
        parts = []
        parts.append(self.verb)
        parts.append(self.time.isoformat())
        if self.actor is not None:
            parts.append(self.actor.foreign_id)
        else:
            parts.append("")

        if self.object is not None:
            parts.append(self.object.foreign_id)
        else:
            parts.append("")

        if self.target is not None:
            parts.append(self.target.foreign_id)
        else:
            parts.append("")

        print "Base string for save is "+(" ".join(parts))

        hash = sha1_hex("\t".join(parts))
        self.uniq_hash = hash

        print "Hash for save is "+hash
        print "Id for save is "+repr(self.id)

        super(Activity, self).save()


def sha1_hex(s):
    m = hashlib.sha1()
    m.update(s)
    return m.hexdigest()
