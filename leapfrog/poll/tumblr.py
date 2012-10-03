from __future__ import division

from base64 import b64decode
from datetime import datetime
import json
import logging
import re
import socket
from urllib import urlencode
from urlparse import urlparse, urlunparse
from xml.etree import ElementTree

from BeautifulSoup import BeautifulSoup
from django.conf import settings
import httplib2
import oauth2 as oauth

from leapfrog.models import Object, Account, Media, Person, UserStream, UserReplyStream
import leapfrog.poll.embedlam


log = logging.getLogger(__name__)


def account_for_tumblr_shortname(shortname):
    try:
        # We don't have any data to update the account with, so whatever we have is fine.
        return Account.objects.get(service='tumblr.com', ident=shortname)
    except Account.DoesNotExist:
        pass

    csr = oauth.Consumer(*settings.TUMBLR_CONSUMER)
    url = 'http://api.tumblr.com/v2/blog/%s.tumblr.com/info?api_key=%s' % (shortname, csr.key)

    http = httplib2.Http()
    resp, cont = http.request(url)
    if resp.status == 500:
        log.info("Server error fetching tumblr info %s (is Tumblr down?)", account.ident)
        return
    if resp.status == 408:
        log.info("Timeout fetching tumblr info %s (is Tumblr down/slow?)", account.ident)
        return
    if resp.status == 401:
        log.info("401 Unauthorized fetching tumblr info %s (maybe suspended?)", account.ident)
        return
    if resp.status == 403:
        raise ValueError("403 Forbidden fetching tumblr info %s\n\n%s" % (account.ident, cont))
    if resp.status != 200:
        raise ValueError("Unexpected HTTP response %d %s fetching tumblr info %s" % (resp.status, resp.reason, account.ident))

    data = json.loads(cont)
    blogdata = data['response']['blog']
    display_name = blogdata['title']

    tumblr_avatar_url = 'http://api.tumblr.com/v2/blog/%s.tumblr.com/avatar/64' % shortname
    avatar = Media(
        image_url=tumblr_avatar_url,
        width=64,
        height=64,
    )
    avatar.save()

    person = Person(
        display_name=display_name,
        permalink_url=blogdata['url'],
        avatar=avatar,
    )
    person.save()

    account = Account(
        service='tumblr.com',
        ident=shortname,
        display_name=blogdata['title'],
        person=person,
    )
    account.save()

    return account


def account_for_tumblr_userinfo(userinfo, person=None):
    username = userinfo['name']
    try:
        account = Account.objects.get(service='tumblr.com', ident=username)
    except Account.DoesNotExist:
        pass
    else:
        person = account.person
        if not person.avatar_source or person.avatar_source == 'tumblr.com':
            (primary_blog,) = [blog for blog in userinfo['blogs'] if blog.get('primary', False)]
            tumblr_avatar_url = 'http://api.tumblr.com/v2/blog/%s.tumblr.com/avatar/64' % primary_blog['name']
            if not person.avatar or person.avatar.image_url != tumblr_avatar_url:
                avatar = Media(
                    image_url=tumblr_avatar_url,
                    width=64,
                    height=64,
                )
                avatar.save()
                person.avatar = avatar
                person.avatar_source = 'tumblr.com'
                person.save()
            elif not person.avatar_source:
                person.avatar_source = 'tumblr.com'
                person.save()
        return account

    (primary_blog,) = [blog for blog in userinfo['blogs'] if blog.get('primary', False)]
    display_name = primary_blog.get('title', username)
    if person is None:
        tumblr_avatar_url = 'http://api.tumblr.com/v2/blog/%s.tumblr.com/avatar/64' % primary_blog['name']
        avatar = Media(
            image_url=tumblr_avatar_url,
            width=64,
            height=64,
        )
        avatar.save()

        person = Person(
            display_name=display_name,
            permalink_url=primary_blog['url'],
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


def account_for_tumblelog_element(tumblelog_elem, person=None):
    account_name = tumblelog_elem.attrib['name']
    try:
        account = Account.objects.get(service='tumblr.com', ident=account_name)
    except Account.DoesNotExist:
        pass
    else:
        person = account.person
        if not person.avatar_source or person.avatar_source == 'tumblr.com':
            try:
                tumblr_avatar_url = tumblelog_elem.attrib['avatar-url-64']
            except KeyError:
                pass
            else:
                if not person.avatar or person.avatar.image_url != tumblr_avatar_url:
                    avatar = Media(
                        image_url=tumblr_avatar_url,
                        width=64,
                        height=64,
                    )
                    avatar.save()
                    person.avatar = avatar
                    person.avatar_source = 'tumblr.com'
                    person.save()
                elif not person.avatar_source:
                    person.avatar_source = 'tumblr.com'
                    person.save()
        return account

    display_name = tumblelog_elem.attrib.get('title', account_name)
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


def remove_reblog_boilerplate_from_obj(obj, in_reply_to):
    soup = BeautifulSoup(obj.body)
    top_two = soup.findAll(recursive=False, limit=2)
    if len(top_two) < 2:
        return
    maybe_p, maybe_quote = top_two

    if maybe_quote.name != 'blockquote':
        log.debug('Second element is a %s, not a blockquote', maybe_quote.name)
        return
    if maybe_p.name != 'p':
        log.debug('First element is a %s, not a p', maybe_p.name)
        return
    maybe_blog_link = maybe_p.find(name='a', attrs={'href': in_reply_to.permalink_url})
    if not maybe_blog_link:
        log.debug("First element doesn't link to reply target %s in its HTML: %s",
            in_reply_to.permalink_url, unicode(maybe_p).encode('utf8', 'ignore'))
        return

    maybe_p.extract()
    maybe_quote.extract()
    obj.body = str(soup).decode('utf8').strip()


def object_from_postdata(postdata):
    tumblr_id = postdata['id']
    try:
        return False, Object.objects.get(service='tumblr.com', foreign_id=tumblr_id)
    except Object.DoesNotExist:
        pass

    obj = Object(
        service='tumblr.com',
        foreign_id=tumblr_id,
        permalink_url=postdata['post_url'],
        title='',
        body='',
        render_mode='mixed',
        time=datetime.strptime(postdata['date'], '%Y-%m-%d %H:%M:%S GMT'),
        author=account_for_tumblr_shortname(postdata['blog_name']),
    )

    post_type = postdata['type']
    if post_type == 'regular':
        obj.title = postdata.get('title', '')
        obj.body = postdata.get('body', '')
    elif post_type == 'video':
        player = max((player for player in postdata['player'] if player['width'] <= 700), key=lambda pl: pl['width'])
        body = player['embed_code']
        caption = postdata.get('caption', None)
        if caption:
            body = '\n\n'.join((body, caption))
        obj.body = body
    elif post_type == 'audio':
        obj.title = postdata.get('track_name', '')
        artist = postdata.get('artist', '')
        if artist and obj.title:
            obj.title = u'%s \u2013 %s' % (artist, obj.title)
        elif artist:
            obj.title = artist

        body = postdata.get('player', '')
        album_art = postdata.get('album_art', '')
        if album_art:
            body = u'\n\n'.join((u'<p><img src="%s"></p>' % album_art, body))
        caption = postdata.get('caption', '')
        if caption:
            body = u'\n\n'.join((body, caption))

        obj.body = body
    elif post_type == 'photo' and len(postdata['photos']) > 1:  # photoset
        photobodies = list()

        for photo in postdata['photos']:
            photosize = max((size for size in photo['alt_sizes'] if size['width'] <= 700), key=lambda sz: sz['width'])
            body = u'<p><img src="%(url)s" width="%(width)s" height="%(height)s"></p>' % photosize
            photobodies.append(body)
            caption = photo.get('caption', '')
            if caption:
                photobodies.append(u'<p>%s</p>' % photo['caption'])

        caption = postdata.get('caption', '')
        if caption:
            photobodies.append(caption)

        obj.body = u'\n\n'.join(photobodies)
    elif post_type == 'photo':  # single photo
        photo = postdata['photos'][0]
        photosize = max((size for size in photo['alt_sizes'] if size['width'] <= 700), key=lambda sz: sz['width'])

        image = Media(
            image_url=photosize['url'],
            width=photosize['width'],
            height=photosize['height'],
        )
        image.save()

        obj.image = image
        obj.render_mode = 'image'

        obj.body = postdata.get('caption', '')
    elif post_type == 'link':
        # TODO: display the link if we can't make an in_reply_to object.
        # handle the Page manually to always provide an in_reply_to?
        # should this just be a render_mode=link object itself instead
        # of a reply?
        link_url = postdata['url']
        try:
            in_reply_to_page = leapfrog.poll.embedlam.Page(link_url)
        except ValueError:
            pass
        else:
            try:
                in_reply_to = in_reply_to_page.to_object()
            except ValueError:
                in_reply_to = None
            if in_reply_to is None:
                in_reply_to = Object(
                    service='',
                    foreign_id=in_reply_to_page.url,
                    render_mode='link',
                    title=in_reply_to_page.title,
                    permalink_url=in_reply_to_page.url,
                    time=datetime.utcnow(),
                )
                in_reply_to.save()

            obj.in_reply_to = in_reply_to

        obj.title = postdata.get('title', link_url)
        desc = postdata.get('description', '')
        if desc:
            obj.body = desc
        # If we added no description, make this a share instead.
        elif obj.in_reply_to:
            return True, obj.in_reply_to
    elif post_type == 'quote':
        quote_text = postdata.get('quote', '')
        body = u"""<blockquote><p>%s</p></blockquote>""" % (quote_text,)

        quote_source = postdata.get('source', '')
        if quote_source:
            body = u'\n\n'.join((body, u"<p>\u2014%s</p>" % quote_source))

        obj.body = body

    # TODO: handle chat posts (i guess)
    else:
        log.debug("Unhandled Tumblr post type %r for post #%s; skipping", post_type, tumblr_id)
        return None, None

    # TODO: make reblogs into replies

    obj.save()
    return False, obj


def object_from_post_element(post_el, tumblelog_el):
    tumblr_id = post_el.attrib['id']
    try:
        return False, Object.objects.get(service='tumblr.com', foreign_id=tumblr_id)
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

    post_type = post_el.attrib['type']
    if post_type == 'regular':
        title_el = post_el.find('./regular-title')
        if title_el is not None:
            obj.title = title_el.text
        body_el = post_el.find('./regular-body')
        if body_el is not None:
            obj.body = body_el.text
    elif post_type == 'video':
        body = post_el.find('./video-player').text
        video_caption_el = post_el.find('./video-caption')
        if video_caption_el is not None:
            video_caption = video_caption_el.text
            body = '\n\n'.join((body, video_caption))
        obj.body = body
    elif post_type == 'audio':
        title_el = post_el.find('./id3-title')
        if title_el is not None:
            obj.title = title_el.text
        artist_el = post_el.find('./id3-artist')
        if artist_el is not None:
            obj.title = u'%s \u2013 %s' % (artist_el.text, obj.title)

        body = post_el.find('./audio-player').text
        audio_art_el = post_el.find('./id3-album-art')
        if audio_art_el is not None:
            audio_art_url = audio_art_el.text
            body = u'\n\n'.join((u'<p><img src="%s"></p>' % audio_art_url, body))
        audio_caption_el = post_el.find('./audio-caption')
        if audio_caption_el is not None:
            audio_caption = audio_caption_el.text
            body = u'\n\n'.join((body, audio_caption))
        obj.body = body
    elif post_type == 'photo':
        # TODO: if there's a photo-link-url, is this really a "photo reply"?

        photo_el = sorted(post_el.findall('./photo-url'), key=lambda x: int(x.attrib['max-width']), reverse=True)[0]
        photo_el_width = int(photo_el.attrib['max-width'])
        try:
            width, height = post_el.attrib['width'], post_el.attrib['height']
        except KeyError:
            width, height = None, None
        else:
            width, height = int(width), int(height)
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
            in_reply_to_page = leapfrog.poll.embedlam.Page(link_url)
        except ValueError:
            pass
        else:
            try:
                in_reply_to = in_reply_to_page.to_object()
            except ValueError:
                in_reply_to = None
            if in_reply_to is None:
                in_reply_to = Object(
                    service='',
                    foreign_id=in_reply_to_page.url,
                    render_mode='link',
                    title=in_reply_to_page.title,
                    permalink_url=in_reply_to_page.url,
                    time=datetime.utcnow(),
                )
                in_reply_to.save()

            obj.in_reply_to = in_reply_to

        title_el = post_el.find('./link-text')
        obj.title = link_url if title_el is None else title_el.text
        desc_el = post_el.find('./link-description')
        if desc_el is not None:
            obj.body = desc_el.text

        # If we added no description, make this a share.
        if obj.in_reply_to and not obj.body:
            return True, obj.in_reply_to
    elif post_type == 'quote':
        quote_text = post_el.find('./quote-text').text
        body = u"""<blockquote><p>%s</p></blockquote>""" % (quote_text,)

        quote_source_el = post_el.find('./quote-source')
        if quote_source_el is not None:
            quote_source = quote_source_el.text
            body = u'\n\n'.join((body, u"<p>\u2014%s</p>" % quote_source))

        obj.body = body

    # TODO: handle chat posts (i guess)
    else:
        log.debug("Unhandled Tumblr post type %r for post #%s; skipping", post_type, tumblr_id)
        return None, None

    try:
        orig_url = post_el.attrib['reblogged-root-url']
    except KeyError:
        log.debug("Post #%s is not a reblog, leave it alone", tumblr_id)
    else:
        log.debug("Post #%s is a reblog of %s; let's try walking up", tumblr_id, orig_url)

        really_a_share, orig_obj = False, None
        try:
            really_a_share, orig_obj = object_from_url(orig_url)
        except ValueError, exc:
            # meh
            log.debug("Couldn't walk up to reblog reference %s: %s", orig_url, str(exc))
        if not really_a_share and orig_obj is not None:
            # Patch up the upstream author's userpic if necessary, since we
            # don't get those from /api/read, evidently.
            if orig_obj.author.person.avatar is None and 'reblogged-root-avatar-url-64' in post_el.attrib:
                avatar = Media(
                    image_url=post_el.attrib['reblogged-root-avatar-url-64'],
                    width=64,
                    height=64,
                )
                avatar.save()

                orig_obj.author.person.avatar = avatar
                orig_obj.author.person.save()

                log.debug("Fixed up post #%s's author's avatar to %s", orig_obj.foreign_id, avatar.image_url)

            remove_reblog_boilerplate_from_obj(obj, orig_obj)
            if not obj.body:
                return True, orig_obj

            obj.in_reply_to = orig_obj

    obj.save()
    return False, obj


def object_from_url(url):
    urlparts = urlparse(url)
    mo = re.match(r'/post/(\d+)', urlparts.path)  # the path, not the whole url
    if mo is None:
        log.debug("URL %r did not match Tumblr URL pattern", url)
        return None, None
    tumblr_id = mo.group(1)

    # We might try to short-circuit to the Object table here, but the link
    # might just share an existing Tumblr post ID. Let's always go to the
    # API here, just to make sure.

    query = urlencode({'id': tumblr_id})
    api_url = urlunparse(('http', 'tumblr.com', '/api/read', None, query, None))

    client = httplib2.Http()
    client.follow_redirects = False

    while True:
        resp, cont = client.request(api_url, headers={'Host': urlparts.netloc})
        if resp.status not in (301, 303, 307):
            break
        urlparts = urlparse(resp['location'])
        api_url = urlunparse(('http', 'tumblr.com', urlparts.path, urlparts.params, urlparts.query, urlparts.fragment))

    if resp.status == 500:
        raise ValueError("Server error asking about Tumblr post #%s (is Tumblr down?)" % tumblr_id)
    if resp.status != 200:
        raise ValueError("Unexpected response asking about Tumblr post #%s: %d %s"
            % (tumblr_id, resp.status, resp.reason))
    content_type = resp.get('content-type')
    if content_type is None:
        raise ValueError("Response asking about Tumblr post #%s unexpectedly had no content type (is Tumblr down?)" % tumblr_id)
    if not content_type.startswith('text/xml'):
        raise ValueError("Unexpected response of type %r asking about Tumblr post #%s"
            % (content_type, tumblr_id))

    doc = ElementTree.fromstring(cont.lstrip())
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

    try:
        resp, cont = client.request('http://api.tumblr.com/v2/user/dashboard')
    except socket.error:
        log.info("Socket error polling Tumblr user %s's dashboard (is Tumblr down?)", account.ident)
        return

    if resp.status == 500:
        log.info("Server error polling Tumblr user %s's dashboard (is Tumblr down?)", account.ident)
        return
    if resp.status == 408:
        log.info("Timeout polling Tumblr user %s's dashboard (is Tumblr down/slow?)", account.ident)
        return
    if resp.status == 401:
        log.info("401 Unauthorized fetching Tumblr user %s's dashboard (maybe suspended?)", account.ident)
        return
    if resp.status == 403:
        raise ValueError("403 Forbidden fetching Tumblr user %s's dashboard\n\n%s" % (account.ident, cont))

    if resp.status != 200:
        raise ValueError("Unexpected HTTP response %d %s looking for dashboard for Tumblr user %s" % (resp.status, resp.reason, account.ident))

    content_type = resp.get('content-type')
    if content_type is None:
        log.info("Response polling Tumblr user %s's dashboard had no content type (is Tumblr down?)", account.ident)
        return
    if not content_type.startswith('application/json'):
        log.info("Unexpected response of type %r looking for dashboard for Tumblr user %s (expected application/json)", content_type, account.ident)
        return

    data = json.loads(cont)
    for postdata in data['response']['posts']:
        really_a_share, obj = object_from_postdata(postdata)
        if obj is None:
            continue
        why_account = account_for_tumblr_shortname(postdata['blog_name']) if really_a_share else obj.author

        root = obj
        why_verb = 'share' if really_a_share else 'post'
        while root.in_reply_to is not None:
            root = root.in_reply_to
            why_verb = 'share' if really_a_share else 'reply'

        now = datetime.utcnow()
        stream_time = obj.time if obj.time <= now else now
        streamitem, created = UserStream.objects.get_or_create(user=user, obj=root,
            defaults={'time': stream_time, 'why_account': why_account, 'why_verb': why_verb})

        superobj = obj
        while superobj.in_reply_to is not None:
            stream_time = superobj.time if superobj.time <= now else now
            UserReplyStream.objects.get_or_create(user=user, root=root, reply=superobj,
                defaults={'root_time': streamitem.time, 'reply_time': stream_time})
            superobj = superobj.in_reply_to
