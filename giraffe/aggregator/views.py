import xml.etree.ElementTree as etree

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from giraffe.aggregator import models
import giraffe.aggregator.activitystreams.atom as as_atom


def activity_stream(request):
    return HttpResponse('foo')


@csrf_exempt
def callback(request, sub_pk):
    method = request.method
    subscription = models.Subscription.objects.get(id=sub_pk)

    if method == "POST":
        feed_str = request.raw_post_data

        et = etree.fromstring(feed_str)
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
                logging.debug("Loaded activity %r", activity.id)
            except models.Activity.DoesNotExist:
                pass

            import logging

            if activity is None:
                logging.debug("Making a new activity")
                activity = models.Activity()

            if verb is not None:
                verb = verb.replace("http://activitystrea.ms/schema/1.0/", "", 1)
            else:
                verb = ''

            activity.object = object
            activity.actor = actor
            activity.target = target
            activity.time = time
            activity.verb = verb
            activity.subscription = subscription

            if subscription.user is not None:
                activity.user = subscription.user

            activity.save()

            return HttpResponse("THANKS!")

    else:
        requested_topic_url = request.GET["hub.topic"]

        if subscription.topic_url != requested_topic_url:
            return HttpResponse("WRONG!", status=400, content_type="text/plain")

        subscription.mode = "push"
        subscription.save()

        return HttpResponse(request.GET["hub.challenge"])



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
    else:
        object_type = ''

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

