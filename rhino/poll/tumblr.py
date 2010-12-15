from __future__ import division

from base64 import b64decode
from datetime import datetime
import logging
import re
from urllib import urlencode
from urlparse import urlparse, urlunparse
from xml.etree import ElementTree

from django.conf import settings
import httplib2
import oauth2 as oauth

from rhino.models import Object, Account, Media, Person, UserStream, UserReplyStream
import rhino.poll.embedlam


log = logging.getLogger(__name__)


def account_for_tumblelog_element(tumblelog_elem, person=None):
    account_name = tumblelog_elem.attrib['name']
    try:
        return Account.objects.get(service='tumblr.com', ident=account_name)
    except Account.DoesNotExist:
        pass

    display_name = tumblelog_elem.attrib['title']
    if person is None:
        try:
            host = tumblelog_elem.attrib['cname']
        except KeyError:
            host = '%s.tumblr.com' % tumblelog_elem.attrib['name']

        avatar = None
        if 'avatar-url-64' in tumblelog_elem.attrib:
            avatar = Media(
                image_url=tumblelog_elem.attrib['avatar-url-64'],
                width=64,
                height=64,
            )
            avatar.save()

        person = Person(
            display_name=display_name,
            permalink_url='http://%s/' % host,
            avatar=avatar,
        )
        person.save()

    account = Account(
        service='tumblr.com',
        ident=account_name,
        display_name=display_name,
        person=person,
    )
    account.save()

    return account


def object_from_post_element(post_el, tumblelog_el):
    tumblr_id = post_el.attrib['id']
    try:
        return Object.objects.get(service='tumblr.com', foreign_id=tumblr_id)
    except Object.DoesNotExist:
        pass

    obj = Object(
        service='tumblr.com',
        foreign_id=tumblr_id,
        permalink_url=post_el.attrib['url-with-slug'],
        title='',
        body='',
        render_mode='mixed',
        time=datetime.strptime(post_el.attrib['date-gmt'], '%Y-%m-%d %H:%M:%S GMT'),
        author=account_for_tumblelog_element(tumblelog_el),
    )

    # TODO: handle reblogs (there'll be reblogged-from-url and reblogged-root-url attributes)

    post_type = post_el.attrib['type']
    if post_type == 'regular':
        obj.title = post_el.find('./regular-title').text
        obj.body = post_el.find('./regular-body').text
    elif post_type == 'video':
        video_player = post_el.find('./video-player').text
        video_caption = post_el.find('./video-caption').text
        obj.body = '\n\n'.join((video_player, video_caption))
    elif post_type == 'photo':
        # TODO: if there's a photo-link-url, is this really a "photo reply"?

        width, height = int(post_el.attrib['width']), int(post_el.attrib['height'])
        photo_el = sorted(post_el.findall('./photo-url'), key=lambda x: int(x.attrib['max-width']), reverse=True)[0]
        photo_el_width = int(photo_el.attrib['max-width'])
        if width > photo_el_width:
            height = photo_el_width * height / width
            width = photo_el_width

        image = Media(
            image_url=photo_el.text,
            width=width,
            height=height,
        )
        image.save()

        obj.image = image
        obj.render_mode = 'image'

        caption_el = post_el.find('./photo-caption')
        if caption_el is not None:
            obj.body = caption_el.text
    elif post_type == 'link':
        # TODO: display the link if we can't make an in_reply_to object.
        # handle the Page manually to always provide an in_reply_to?
        # should this just be a render_mode=link object itself instead
        # of a reply?
        link_url = post_el.find('./link-url').text
        try:
            in_reply_to = rhino.poll.embedlam.object_for_url(link_url)
        except ValueError:
            pass
        else:
            obj.in_reply_to = in_reply_to

        obj.title = post_el.find('./link-text').text
        obj.body = post_el.find('./link-description').text
    # TODO: handle audio posts
    # TODO: handle quote posts
    # TODO: handle chat posts (i guess)
    else:
        log.debug("Unhandled Tumblr post type %r for post #%s; skipping", post_type, tumblr_id)
        return

    obj.save()
    return obj


def object_from_url(url):
    urlparts = urlparse(url)
    mo = re.match(r'/post/(\d+)', urlparts.path)  # the path, not the whole url
    if mo is None:
        return
    tumblr_id = mo.group(1)

    # We might try to short-circuit to the Object table here, but the link
    # might just share an existing Tumblr post ID. Let's always go to the
    # API here, just to make sure.

    query = urlencode({'id': tumblr_id})
    api_url = urlunparse(('http', urlparts.netloc, '/api/read', None, query, None))

    client = httplib2.Http()
    resp, cont = client.request(api_url)
    if resp.status != 200:
        raise ValueError("Unexpected response asking about Tumblr post #%d: %d %s"
            % (tumblr_id, resp.status, resp.reason))

    doc = ElementTree.fromstring(cont)
    tumblelog_el = doc.find('./tumblelog')
    post_el = doc.find('./posts/post')

    return object_from_post_element(post_el, tumblelog_el)


def poll_tumblr(account):
    user = account.person.user
    if user is None:
        return

    csr = oauth.Consumer(*settings.TUMBLR_CONSUMER)
    token = oauth.Token(*account.authinfo.split(':', 1))
    client = oauth.Client(csr, token)
    body = urlencode({'num': 30})
    resp, cont = client.request('http://www.tumblr.com/api/dashboard', method='POST', body=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if resp.status != 200:
        raise ValueError("Unexpected HTTP response %d %s looking for dashboard for Tumblr user %s" % (resp.status, resp.reason, email))

    doc = ElementTree.fromstring(cont)
    for post_el in doc.findall('./posts/post'):
        obj = object_from_post_element(post_el, post_el.find('./tumblelog'))
        if obj is None:
            continue

        root = obj
        why_verb = 'post'
        while root.in_reply_to is not None:
            root = root.in_reply_to
            why_verb = 'reply'

        UserStream.objects.get_or_create(user=user, obj=root,
            defaults={'time': obj.time, 'why_account': obj.author, 'why_verb': why_verb})

        superobj = obj
        while superobj.in_reply_to is not None:
            UserReplyStream.objects.get_or_create(user=user, root=root, reply=superobj,
                defaults={'root_time': root.time, 'reply_time': superobj.time})
            superobj = superobj.in_reply_to
