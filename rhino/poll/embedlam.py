from datetime import datetime
import feedparser
from HTMLParser import HTMLParseError
import json
import logging
import re
import socket
from urllib import urlencode
from urlparse import urlparse, urljoin

from BeautifulSoup import BeautifulSoup
import httplib2
from mimeparse import parse_mime_type

from rhino.models import Account, Object, Person, Media
import rhino.poll.flickr
import rhino.poll.tumblr
import rhino.poll.twitter
import rhino.poll.typepad
import rhino.poll.vimeo


log = logging.getLogger(__name__)


def account_for_embed_resource(resource):
    url = resource['author_url']
    try:
        return Account.objects.get(service='', ident=url)
    except Account.DoesNotExist:
        pass

    # TODO: go find an avatar by way of ~~=<( MAGIC )>=~~
    person = Person(
        display_name=resource['author_name'],
    )
    person.save()
    acc = Account(
        service='',
        ident=url,
        display_name=resource['author_name'],
        person=person,
    )
    acc.save()

    return acc


def object_from_oembed(endpoint_url, target_url, discovered=False):
    try:
        return Object.objects.get(service='', foreign_id=target_url)
    except Object.DoesNotExist:
        pass

    if not discovered:
        endpoint_url = '%s?%s' % (endpoint_url, urlencode({'format': 'json', 'url': target_url}))

    h = httplib2.Http()
    resp, cont = h.request(endpoint_url, headers={'User-Agent': 'rhino/1.0'})
    if resp.status != 200:
        raise ValueError("Unexpected response requesting OEmbed data %s: %d %s" % (endpoint_url, resp.status, resp.reason))

    resource = json.loads(cont)

    try:
        resource_type = resource['type']
    except KeyError:
        log.debug("wtf is %r", resource)
        raise ValueError("Resource from OEmbed request %s has no 'type'" % (endpoint_url,))

    if resource_type == 'video':
        obj = Object(
            service='',
            foreign_id=target_url,
            render_mode='mixed',
            title=resource['title'],
            body=resource['html'],
            author=account_for_embed_resource(resource),
            time=datetime.now(),
            permalink_url=target_url,
        )
        obj.save()
        return obj
    elif resource_type in ('photo', 'image'):
        image = Media(
            image_url=resource['url'],
            width=resource['width'],
            height=resource['height'],
        )
        image.save()
        obj = Object(
            service='',
            foreign_id=target_url,
            render_mode='image',
            title=resource['title'],
            image=image,
            author=account_for_embed_resource(resource),
            time=datetime.now(),
            permalink_url=target_url,
        )
        obj.save()
        return obj

    raise ValueError('Unknown OEmbed resource type %r' % resource_type)


def title_from_html_head(head):
    og_title_elem = head.find("meta", property="og:title")
    old_facebook_title_elem = head.find("meta", {"name":"title"})
    title_elem = head.find("title")
    title = value_for_meta_elems((og_title_elem, old_facebook_title_elem, title_elem), "")
    return title


def object_from_html_head(url, orig_url, head):
    title = title_from_html_head(head)

    og_image_elem = head.find("meta", property="og:image")
    old_facebook_image_elem = head.find("link", rel="image_src")
    image_url = value_for_meta_elems((og_image_elem, old_facebook_image_elem), base_url=orig_url)

    og_summary_elem = head.find("meta", property="og:description")
    summary = value_for_meta_elems((og_summary_elem,), "")

    if not image_url and not summary:
        log.debug("Found neither an image URL nor a summary for %s, so returning no object", url)
        return None

    image = None
    if image_url:
        image = Media()
        image.image_url = image_url
        # TODO: how big is this image?
        image.save()

    render_mode = 'link'
    if re.match(r'http:// (?: instagr\.am | yfrog\.com ) /', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
        render_mode = 'image'

    obj = Object(
        service='',
        foreign_id=url,
        render_mode=render_mode,
        title=title,
        body=summary,
        permalink_url=url,
        time=datetime.now(),
        image=image,
    )
    obj.save()

    return obj


def object_from_feed_entry(feed_url, item_url):
    feed = feedparser.parse(feed_url)
    matching_entries = [ entry for entry in feed.entries if entry.link == item_url ]
    if len(matching_entries) > 0:
        entry = matching_entries[0]
    else:
        return None

    obj = Object(
        service='',
        foreign_id=item_url,
        title=entry.title,
        permalink_url=item_url,
    )

    # If we have full content then this becomes a "mixed". Otherwise, we
    # marshall it as a link.
    if "content" in entry and len(entry.content) > 0:
        obj.render_mode = 'mixed'
        obj.body = entry.content[0].value
    else:
        obj.render_mode = 'link'
        obj.body = entry.summary if "summary" in entry else ""

    object_time = None
    if "published_parsed" in entry:
        object_time = entry.published_parsed
    elif "updated_parsed" in entry:
        object_time = entry.updated_parsed

    if object_time is None:
        log.debug("Feed item %s has no timestamp, so making no object", item_url)
        return None

    obj.time = datetime(*object_time[:6])
    obj.save()

    return obj


def object_from_photo_url(url, width, height):
    try:
        return Object.objects.get(service='', foreign_id=url)
    except Object.DoesNotExist:
        pass

    log.debug("Treating %s as a photo URL and making an image object from it", url)
    image = Media(
        image_url=url,
        width=width,
        height=height,
    )
    image.save()
    obj = Object(
        service='',
        foreign_id=url,
        render_mode='image',
        title='',
        image=image,
        author=None,
        time=datetime.now(),
        permalink_url=url,
    )
    obj.save()
    return obj


def value_for_meta_elems(elems, default=None, base_url=None):
    for elem in elems:
        if elem is None:
            continue

        value = None

        if elem.has_key("content"):
            value = elem["content"]

        # Matches link href="..."
        elif elem.has_key("href"):
            value = elem["href"]

        # Matches <title>...</title>
        elif elem.string:
            value = elem.string

        # Some poor, confused souls publish meta value="..."
        elif elem.has_key("value"):
            value = elem["value"]

        if value:
            return urljoin(base_url, value) if base_url else value

    return default


class Page(object):

    def __init__(self, url):
        self.content = ''
        self.orig_url = url
        self.url = url
        self.type = 'html'

        # These we can already ask about by URL, so don't bother fetching about them.
        if re.match(r'http:// (?: [^/]* flickr\.com/photos/[^/]+/\d+ | twitpic\.com/\w+ | twitter\.com/ (?: \#!/ )? [^/]+/ status/ (\d+) | vimeo\.com/ \d+ )', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            return

        # Fetch the resource and soupify it.
        h = httplib2.Http(timeout=10)
        try:
            resp, content = h.request(url, headers={'User-Agent': 'rhino/1.0'})
        except socket.timeout:
            raise ValueError("Request to %s timed out" % url)
        except httplib2.RedirectLimit:
            raise ValueError("%s redirected too many times" % url)
        except httplib2.ServerNotFoundError, exc:
            raise ValueError(str(exc))

        if resp.status != 200:
            raise ValueError("Unexpected response discovering %s: %d %s" % (url, resp.status, resp.reason))
        url = resp['content-location']

        content_type_str = resp.get('content-type')
        if content_type_str is None or '/' not in content_type_str:
            content_type_str = 'application/x-unknown'
        content_type = parse_mime_type(content_type_str)
        if content_type[0] == 'image':
            log.debug("This seems to be an image")
            self.type = 'image'
            return

        if content_type[0:2] != ('text', 'html'):
            # hmm
            raise ValueError("Unsupported content type %s/%s for resource %s" % (content_type[0], content_type[1], url))

        try:
            soup = BeautifulSoup(content)
        except HTMLParseError, exc:
            raise ValueError("Could not parse HTML response for %s: %s" % (url, str(exc)))
        head = soup.head
        if head is None:
            raise ValueError('Could not discover against HTML target %s with no head' % url)

        # What's the real URL?
        orig_url = url
        og_url_elem = head.find("meta", property="og:url")
        canon_elem = head.find('link', rel='canonical')
        canon_url = value_for_meta_elems((og_url_elem, canon_elem), base_url=orig_url)

        if canon_url is not None:
            # Only allow this canonicalization if it's at the same domain as the original URL.
            orig_host = urlparse(url)[1]
            canon_host = urlparse(canon_url)[1]
            if orig_host == canon_host:
                log.debug('Decided canonical URL for %s is %s, so using that', url, canon_url)
                url = canon_url

        self.url = url
        self.content = content
        self.soup = soup

    @property
    def title(self):
        try:
            return title_from_html_head(self.soup.head)
        except AttributeError:
            return None

    @property
    def permalink_url(self):
        return self.url

    def to_object(self):
        url = self.url

        # If this URL points directly at an image then let's make a photo object
        if self.type == "image":
            # TODO: Inspect the image header to find out what size the image is
            return object_from_photo_url(url, None, None)

        if re.match(r'http:// [^/]* flickr\.com/photos/[^/]+/\d+', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            return rhino.poll.flickr.object_from_url(url)
        if re.match(r'http://twitpic\.com/ \w+ ', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            return rhino.poll.twitter.object_from_twitpic_url(url)
        if re.match(r'http://twitter\.com/ (?: \#!/ )? [^/]+/ status/ (\d+)', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            return rhino.poll.twitter.object_from_url(url)
        if re.match(r'http://vimeo\.com/ \d+', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            return rhino.poll.vimeo.object_from_url(url)

        # If it looks like a Tumblr URL, try asking Tumblr about it.
        if re.match(r'http://[^/]+/post/\d+', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            try:
                return rhino.poll.tumblr.object_from_url(url)
            except ValueError:
                # Keep trying the regular way.
                pass

        # If the site mentions TypePad, try asking TypePad about it.
        is_typepad_url = re.match(r'http:// .* \.typepad\.com/', url, re.MULTILINE | re.DOTALL | re.VERBOSE)
        mentions_typepad = lambda: re.search(r'typepad', self.content, re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)
        if is_typepad_url or mentions_typepad():
            try:
                return rhino.poll.typepad.object_from_url(url)
            except ValueError:
                # Keep trying the regular way.
                pass

        try:
            return Object.objects.get(service='', foreign_id=url)
        except Object.DoesNotExist:
            pass  # time to make the donuts

        try:
            head = self.soup.head
        except AttributeError:
            raise ValueError("Thought URL %s would be handled specially but it wasn't" % self.url)

        # Does it support OEmbed?
        oembed_node = head.find(rel='alternate', type='application/json+oembed')
        # TODO: support xml?
        if oembed_node is not None:
            log.debug('Finding object for %s through OEmbed', url)
            return object_from_oembed(oembed_node['href'], url, discovered=True)

        # Does it have a feed declared? If so, let's go hunting in the feed for
        # an entry corresponding to this page.
        atom_feed_link = head.find(rel='alternate', type='application/atom+xml')
        rss_feed_link = head.find(rel='alternate', type='application/rss+xml')
        feed_url = value_for_meta_elems((atom_feed_link, rss_feed_link), base_url=self.orig_url)
        if feed_url:
            object = object_from_feed_entry(feed_url, url)
            if object:
                log.debug('Found object for %s through the feed', url)
                return object

        log.debug('Finding object for %s from the existing HTML head data', url)
        return object_from_html_head(url, self.orig_url, head)


def object_for_url(url):
    """Returns a saved `rhino.models.Object` for the resource at the URL
    ``url``.

    If the resulting object has only a title (neither body content nor a
    representative image), this function will return ``None`` instead of
    an `Object` instance.

    """
    return Page(url).to_object()
