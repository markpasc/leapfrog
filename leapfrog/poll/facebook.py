from datetime import datetime
import json
import logging
import re
import cgi

from django.conf import settings
import httplib2
import oauth2 as oauth
from urllib import urlencode
from urlparse import urlunparse

from leapfrog.models import Object, Account, Person, UserStream, Media, UserReplyStream
import leapfrog.poll.embedlam


log = logging.getLogger(__name__)


def poll_facebook(account):
    user = account.person.user
    if user is None:
        log.debug("No user attached to account %r. Skipping.", account)
        return

    access_token = account.authinfo
    if not access_token:
        log.error("Account %r has no authinfo. Ignoring.", account)
        # Nothing to do!
        return

    # Now find out who this user is
    query = { 'access_token': access_token }
    url = urlunparse(('https', 'graph.facebook.com', 'me/home', None, urlencode(query), None))
    log.debug("Fetching news feed for %r from %s", account, url)
    h = httplib2.Http()
    resp, content = h.request(url, method='GET')
    feed = json.loads(content)

    if 'error' in feed:
        if feed['error']['type'] == 'OAuthException':
            # User probably changed their password. Ignore it.
            log.debug("Facebook returned OAuthException I'm ignoring: %s", feed['error']['message'])
            return
        log.error("Facebook returned %s: %s", feed['error']['type'], feed['error']['message'])
        return
    if 'data' not in feed:
        log.error("Facebook returned unexpected data-free feed for %s (%s): %r", account.display_name, account.ident, feed)
        return

    items = feed["data"]

    for item in reversed(items):

        try:
            id = item["id"]

            # we only care about "link" and "video".
            # "video" is just a funny case of link in facebook anyway.
            # This specifically ignores "status", since I don't think
            # Facebook statuses really qualify as interesting content
            # by the definition this application uses.
            type = item["type"]

            if type != "link" and type != "video":
                log.debug("Ignoring %s because it's a %s", id, type)
                continue

            log.debug("Trying to make an object for this Facebook %s item %s", type, id)

            (orig_obj, actor) = object_for_facebook_item(item, requesting_account=account)
            if orig_obj is None or actor is None:
                # Skipped for some reason inside object_for_facebook_item
                log.debug("Skipped item %s", id)
                continue

            log.debug("Wrangling Facebook item %s produced object %r", id, orig_obj)

            why_verb = "share"

            obj = orig_obj
            # Walk up until we get to the toplevel item
            while obj.in_reply_to is not None:
                # If there's something in here that's from facebook.com
                # then it's a reply we created inside object_for_facebook_item
                if obj.service == "facebook.com":
                    why_verb = "reply"

                obj = obj.in_reply_to

            log.debug("Creating a UserStream row for object %r which is a %s by %r", obj, why_verb, actor)
            streamitem, created = UserStream.objects.get_or_create(user=user, obj=obj,
                defaults={'why_account': actor, 'why_verb': why_verb, 'time': orig_obj.time})

            # Now walk up again creating UserReplyStream rows as necessary
            reply_obj = orig_obj
            while reply_obj.in_reply_to is not None:
                UserReplyStream.objects.get_or_create(user=user, root=obj, reply=reply_obj,
                    defaults={'root_time': streamitem.time, 'reply_time': reply_obj.time})
                reply_obj = reply_obj.in_reply_to


        except Exception, exc:
            from sentry.client.base import SentryClient
            SentryClient().create_from_exception(view=__name__)


def account_for_facebook_user(fb_user, person=None):
    try:
        account = Account.objects.get(service='facebook.com', ident=fb_user["id"])
    except Account.DoesNotExist:
        if person is None:
            avatar = Media(
                width=50,
                height=50,
                image_url='http://graph.facebook.com/%s/picture' % fb_user["id"]
            )
            avatar.save()
            person = Person(
                display_name=fb_user["name"],
                avatar=avatar,
                permalink_url=fb_user["link"],
            )
            person.save()
        account = Account(
            service='facebook.com',
            ident=fb_user["id"],
            display_name=fb_user["name"],
            person=person,
        )
        account.save()

    return account


def account_for_facebook_uid(fb_uid, requesting_account=None, person=None):
    try:
        # Avoid doing this followup HTTP request if we already have an account.
        account = Account.objects.get(service='facebook.com', ident=fb_uid)
    except Account.DoesNotExist:
        log.debug("Need to fetch the user object for as-yet-unseen facebook user %s", fb_uid)

        query = {}
        if requesting_account is not None:
            query["access_token"] = requesting_account.authinfo

        url = urlunparse(('https', 'graph.facebook.com', fb_uid, None, urlencode(query), None))

        h = httplib2.Http()
        resp, content = h.request(url, method='GET')
        fb_user = json.loads(content)

        # If requesting_account doesn't have access to this account
        # then it'll come back without a link. In this case we
        # pretend the content was anonymous to avoid creating an
        # incomplete account record. This should never happen in
        # practice because content shouldn't show up in your feed
        # unless you have access to see its author.
        if not isinstance(fb_user, dict) or 'link' not in fb_user:
            log.debug("Current user doesn't have access to the author user. Let's just pretend the author is anon.")
            return None

        return account_for_facebook_user(fb_user)


def object_for_facebook_item(item, requesting_account=None):
    fb_id = item["id"]

    try:
        obj = Object.objects.get(service='facebook.com', foreign_id=fb_id)
    except Object.DoesNotExist:
        pass
    else:
        log.debug("Reusing object %r for facebook object %s", obj, fb_id)
        return (obj, obj.author)

    log.debug("Making new object for Facebook item %s", fb_id)

    author = account_for_facebook_uid(item["from"]["id"], requesting_account=requesting_account)

    if author is None:
        log.debug("Can't figure out who the author is, so ignoring this item %s", fb_id)
        return (None, None)

    try:
        referent_url = item['link']
    except KeyError:
        # No URL means no item.
        return None, None

    try:
        referent = leapfrog.poll.embedlam.object_for_url(referent_url)
    except leapfrog.poll.embedlam.RequestError:
        # some expected request error
        return None, None
    except ValueError, exc:
        log.error("Error making object from referent %s of Facebook item %s", referent_url, fb_id)
        log.exception(exc)
        return (None, None)

    if referent is None:
        return (None, None)

    # If "message" is included then this becomes a reply.
    # Otherwise, it's just a share.
    if "message" in item:
        # Facebook doesn't return the URL on Facebook in any predictable way,
        # so we need to synthesize it from the id.
        id_parts = fb_id.split("_")
        if len(id_parts) != 2:
            log.error("id %s is not in the expected format, so skipping", fb_id)
            return referent

        obj = Object(
            service='facebook.com',
            foreign_id=fb_id,
            render_mode='status',
            body=cgi.escape(item["message"]),
            time=datetime.strptime(item['created_time'], '%Y-%m-%dT%H:%M:%S+0000'),
            permalink_url="http://www.facebook.com/%s/posts/%s" % (id_parts[0], id_parts[1]),
            author=author,
            in_reply_to=referent
        )
        obj.save()

        return (obj, author)

    else:

        return (referent, author)



