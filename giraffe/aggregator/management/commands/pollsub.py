

# This is just a temporary development tool to make it
# easier to seed the database with real data.

import django.core.management.base
import urllib2
import xml.etree.ElementTree as etree


from giraffe.aggregator import models
import giraffe.aggregator.activitystreams.atom as as_atom


class Command(django.core.management.base.BaseCommand):
    def handle(self, *args, **kwargs):
        topic_url = args[0]

        try:
            subscription = models.Subscription.lookup_by_topic_url(topic_url)
        except models.Subscription.DoesNotExist:
            print "We do not have a subscription with the url "+topic_url
            return

        req = urllib2.Request(subscription.topic_url)

        try:
            result = urllib2.urlopen(req)
        except urllib2.HTTPError, err:
            print "Failed to fetch content: "+err.code
            return

        print repr(result)

        et = etree.parse(result)
        activities = as_atom.make_activities_from_feed(et)

        for as_activity in activities:

            as_object = as_activity.object
            as_actor = as_activity.actor
            as_target = as_activity.target
            time = as_activity.time
            verb = as_activity.verb

            object = as_object_as_object(as_object)
            actor = as_object_as_object(as_actor)
            target = as_object_as_object(as_target)

            activity = None

            try:
                activity = models.Activity.lookup_by_as_activity(as_activity)
                print "Loaded activity "+repr(activity.id)
            except models.Activity.DoesNotExist:
                pass

            if activity is None:
                print "Making a new activity"
                activity = models.Activity()

            if verb is not None:
                verb = verb.replace("http://activitystrea.ms/schema/1.0/", "", 1)

            activity.object = object
            activity.actor = actor
            activity.target = target
            activity.time = time
            activity.verb = verb
            activity.subscription = subscription

            if subscription.user is not None:
                activity.user = subscription.user

            activity.save()


def as_object_as_object(as_object):

    if as_object is None:
        return None

    foreign_id = as_object.id

    object = None

    if foreign_id:
        try:
            object = models.Object.lookup_by_foreign_id(foreign_id)
        except models.Object.DoesNotExist:
            pass

    if object is None:
        object = models.Object()

    object_type = as_object.object_type
    if object_type is not None:
        object_type = object_type.replace("http://activitystrea.ms/schema/1.0/", "", 1)

    object.foreign_id = foreign_id
    object.name = as_object.name
    object.permalink_url = as_object.url
    object.summary = as_object.summary
    object.object_type = object_type

    if as_object.image is not None:
        object.image_url = as_object.image.url
        object.image_width = as_object.image.width
        object.image_height = as_object.image.height

    if as_object.in_reply_to_object is not None:
        object.in_reply_to = as_object_as_object(as_object.in_reply_to_object)

    object.save()

    return object

