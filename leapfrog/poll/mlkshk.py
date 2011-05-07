import base64
from datetime import datetime
import hashlib
import hmac
import json
import logging
from random import choice
import re
import string
import time
from urlparse import urlparse

from django.conf import settings
import httplib2

from leapfrog.models import Account, Person, Media, Object, UserStream, UserReplyStream
import leapfrog.poll.embedlam


log = logging.getLogger(__name__)


def authstring(**kwargs):
    return 'MAC token="%(token)s", timestamp="%(timestamp)s", nonce="%(nonce)s", signature="%(signature)s"' % kwargs


def sign(uri, method, token, secret):
    timestamp = '%d' % time.time()
    nonce = ''.join(choice(string.letters) for x in xrange(10))
    uriparts = urlparse(uri)
    # TODO: use the real port in the signature when the server bug is fixed
    port = '80'
    normalstring = '\n'.join((token, timestamp, nonce, method, uriparts.netloc, port, uriparts.path, uriparts.query))
    log.debug("Mlkshk authentication base string: %r", normalstring)

    log.debug("Mlkshk authentication secret: %r", secret)
    digest = hmac.new(secret, normalstring, hashlib.sha1).digest()
    log.debug("Mlkshk authentication digest: %r", digest)
    signature = base64.encodestring(digest).strip()
    log.debug("Mlkshk base64 auth string: %r", signature)
    return authstring(token=token, nonce=nonce, timestamp=timestamp, signature=signature)


def call_mlkshk(uri, method='GET', body=None, headers=None, authtoken=None, authsecret=None):
    if headers is None:
        headers = {}

    if authtoken is not None:
        headers['Authorization'] = sign(uri, method, authtoken, authsecret)
        log.debug("Mlkshk authentication header: %r", headers['Authorization'])

    h = httplib2.Http()
    resp, cont = h.request(uri, method, body, headers)
    if resp.status != 200:
        raise ValueError("Unexpected HTTP response %d %s requesting %s" % (resp.status, resp.reason, uri))

    try:
        return json.loads(cont)
    except ValueError, exc:
        raise ValueError("Invalid JSON response requesting %s: %s" % (uri, str(exc)))


def account_for_mlkshk_userinfo(userinfo, person=None):
    account_id = str(userinfo['id'])
    try:
        return Account.objects.get(service='mlkshk.com', ident=account_id)
    except Account.DoesNotExist:
        pass

    username = userinfo['name']
    if person is None:
        # TODO: use mlkshk profile images when we get stabler urls for them
        person = Person(
            display_name=username,
            permalink_url='http://mlkshk.com/user/%s' % username,
        )
        person.save()

    account = Account(
        service='mlkshk.com',
        ident=account_id,
        display_name=username,
        person=person,
    )
    account.save()

    return account


def object_from_url(url):
    urlparts = urlparse(url)
    mo = re.match(r'/[rp]/(\w+)', urlparts.path)  # the path, not the whole url
    if mo is None:
        log.debug("URL %r did not match Mlkshk URL pattern", url)
        return None, None
    mlkshk_id = mo.group(1)

    # Ask the API about it?
    oembed_url = '?'.join(('http://mlkshk.com/services/oembed', urlencode({'url': url})))
    h = httplib2.Http()
    resp, cont = h.request(oembed_url, headers={'User-Agent': 'leapfrog/1.0'})
    if resp.status != 200:
        raise ValueError("Unexpected response asking about MLKSHK post #%s: %d %s"
            % (mlkshk_id, resp.status, resp.reason))

    postdata = json.loads(cont)

    # Mold the OEmbed data into a MLKSHK API shape.
    postdata['user'] = {'name': postdata['author_name']}
    # TODO: ...and so on

    return object_from_post(postdata)


def object_from_post(post, authtoken=None, authsecret=None):
    sharekey = post['permalink_page'].split('/')[-1]

    author = account_for_mlkshk_userinfo(post['user'])
    if not author.person.avatar_source and author.person.avatar is None:
        if authtoken and authsecret:
            userinfo = call_mlkshk('https://mlkshk.com/api/user_id/%s' % author.ident,
                authtoken=authtoken, authsecret=authsecret)
            avatar_url = userinfo['profile_image_url']
            if 'default-icon' not in avatar_url:
                avatar = Media(
                    width=100,
                    height=100,
                    image_url=avatar_url,
                )
                avatar.save()
                author.person.avatar = avatar
                author.person.save()
    posted_at = datetime.strptime(post['posted_at'], '%Y-%m-%dT%H:%M:%SZ')

    if 'url' in post:
        obj = leapfrog.poll.embedlam.object_for_url(post['url'])
        if not post.get('description'):
            return True, obj

        try:
            reply = Object.objects.get(service='mlkshk.com', foreign_id=sharekey)
        except Object.DoesNotExist:
            reply = Object(
                service='mlkshk.com',
                foreign_id=sharekey,
                author=author,
                in_reply_to=obj,
                title=post['title'],
                permalink_url=post['permalink_page'],
                render_mode='mixed',
                body=post['description'],
                time=posted_at,
            )
            reply.save()

        return False, reply

    try:
        obj = Object.objects.get(service='mlkshk.com', foreign_id=sharekey)
    except Object.DoesNotExist:
        photo = Media(
            image_url=post['original_image_url'],
            width=post['width'],
            height=post['height'],
        )
        photo.save()
        obj = Object(
            service='mlkshk.com',
            foreign_id=sharekey,
            image=photo,
        )

    obj.title = post['title']
    obj.author = author
    obj.permalink_url = post['permalink_page']
    obj.render_mode = 'image'
    obj.body = post.get('description') or ''
    obj.time = posted_at
    obj.save()

    # TODO: consider a "save" a share instead of a post?
    return False, obj


def poll_mlkshk(account):
    user = account.person.user
    if user is None:
        return

    token, secret = account.authinfo.encode('utf8').split(':', 1)
    friendshake = call_mlkshk('https://mlkshk.com/api/friends', authtoken=token, authsecret=secret)
    for post in friendshake['friend_shake']:
        really_a_share, obj = object_from_post(post, authtoken=token, authsecret=secret)
        why_account = account_for_mlkshk_userinfo(post['user']) if really_a_share else obj.author

        # Save the root object as a UserStream (with the leaf object's time).
        root = obj
        why_verb = 'share' if really_a_share else 'post'
        while root.in_reply_to is not None:
            root = root.in_reply_to
            why_verb = 'share' if really_a_share else 'reply'

        streamitem, created = UserStream.objects.get_or_create(user=user, obj=root,
            defaults={'time': obj.time, 'why_account': why_account, 'why_verb': why_verb})

        superobj = obj
        while superobj.in_reply_to is not None:
            UserReplyStream.objects.get_or_create(user=user, root=root, reply=superobj,
                defaults={'root_time': streamitem.time, 'reply_time': superobj.time})
            superobj = superobj.in_reply_to
