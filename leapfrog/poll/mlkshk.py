import base64
from datetime import datetime
import hashlib
import hmac
import httplib
import json
import logging
from random import choice
import re
import ssl
import string
import time
from urllib import urlencode
from urlparse import urlparse

from django.conf import settings
from django.utils.html import escape
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

    h = httplib2.Http(disable_ssl_certificate_validation=True)
    try:
        resp, cont = h.request(uri, method, body, headers)
    except httplib.BadStatusLine:
        raise leapfrog.poll.embedlam.RequestError("Bad status line requesting %s (is Mlkshk down?)" % uri)
    except ssl.SSLError, exc:
        raise leapfrog.poll.embedlam.RequestError("SSL error requesting %s: %s (is Mlkshk down?)" % (uri, str(exc)))
    if resp.status == 500:
        raise leapfrog.poll.embedlam.RequestError("500 Server Error requesting %s (is Mlkshk down?)" % uri)
    if resp.status == 502:
        raise leapfrog.poll.embedlam.RequestError("502 Bad Gateway requesting %s (is Mlkshk down?)" % uri)
    if resp.status == 401:
        raise leapfrog.poll.embedlam.RequestError("401 Unauthorized requesting %s (probably an expired token?)" % uri)
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

    try:
        return False, Object.objects.get(service='mlkshk.com', foreign_id=mlkshk_id)
    except Object.DoesNotExist:
        pass

    authtoken, authsecret = settings.MLKSHK_ANONYMOUS_TOKEN
    postdata = call_mlkshk('https://mlkshk.com/api/sharedfile/%s' % mlkshk_id,
        authtoken=authtoken, authsecret=authsecret)

    return object_from_post(postdata, authtoken=authtoken, authsecret=authsecret)


def replacement_text_for_url(url):
    try:
        url_page = leapfrog.poll.embedlam.Page(url)
    except ValueError:
        text = url
    else:
        url = url_page.permalink_url
        text = url_page.title or url

    return r'<a class="aboutlink" href="%s">%s</a>' % (escape(url), escape(text))


def urlized_words(text):
    from django.utils.html import word_split_re, punctuation_re
    from django.utils.http import urlquote
    for word in word_split_re.split(text):
        if '.' in word or ':' in word:
            match = punctuation_re.match(word)
            lead, middle, trail = match.groups()
            if any(middle.startswith(scheme) for scheme in ('http://', 'https://')):
                yield replacement_text_for_url(urlquote(middle, safe='/&=:;#?+*'))
                continue
        yield word


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

    body = post.get('description') or ''
    body = u''.join(urlized_words(body))
    body = re.sub(r'\r?\n', '<br>', body)

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
                body=body,
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
            sfw=not post['nsfw'],
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
    obj.body = body
    obj.time = posted_at
    obj.save()

    # TODO: consider a "save" a share instead of a post?
    return False, obj


def poll_mlkshk(account):
    user = account.person.user
    if user is None:
        return

    token, secret = account.authinfo.encode('utf8').split(':', 1)
    overlap = False
    post = None
    while not overlap:
        if post is None:
            mlkshk_url = 'https://mlkshk.com/api/friends'
        else:
            permalink_page = post['permalink_page']
            sharekey = permalink_page.rsplit('/', 1)[1]
            mlkshk_url = 'https://mlkshk.com/api/friends/before/%s' % sharekey

        try:
            friendshake = call_mlkshk(mlkshk_url, authtoken=token, authsecret=secret)
        except leapfrog.poll.embedlam.RequestError, exc:
            log.info("Expected failure polling friend shake for %s: %s", account.ident, str(exc))
            break
        if not friendshake.get('friend_shake'):
            log.debug("Premature end of friend shake for %s at %s, stopping", account.ident, mlkshk_url)
            break

        for post in friendshake['friend_shake']:
            try:
                really_a_share, obj = object_from_post(post, authtoken=token, authsecret=secret)
            except leapfrog.poll.embedlam.RequestError:
                continue
            why_account = account_for_mlkshk_userinfo(post['user']) if really_a_share else obj.author

            # Save the root object as a UserStream (with the leaf object's time).
            root = obj
            why_verb = 'share' if really_a_share else 'post'
            while root.in_reply_to is not None:
                root = root.in_reply_to
                why_verb = 'share' if really_a_share else 'reply'

            streamitem, created = UserStream.objects.get_or_create(user=user, obj=root,
                defaults={'time': obj.time, 'why_account': why_account, 'why_verb': why_verb})
            if not created:
                log.debug("~~ found existing post %s in stream, about to stop ~~", post['permalink_page'])
                overlap = True

            superobj = obj
            while superobj.in_reply_to is not None:
                UserReplyStream.objects.get_or_create(user=user, root=root, reply=superobj,
                    defaults={'root_time': streamitem.time, 'reply_time': superobj.time})
                superobj = superobj.in_reply_to
