from cookielib import CookieJar, DefaultCookiePolicy
from datetime import datetime
import feedparser
from HTMLParser import HTMLParseError
import httplib
import json
import logging
import re
import socket
import ssl
from urllib import urlencode
from urlparse import urlparse, urljoin

from BeautifulSoup import BeautifulSoup
import httplib2

from leapfrog.models import Account, Object, Person, Media
import leapfrog.poll.flickr
import leapfrog.poll.mlkshk
import leapfrog.poll.tumblr
import leapfrog.poll.twitter
import leapfrog.poll.typepad
import leapfrog.poll.vimeo


log = logging.getLogger(__name__)


def account_for_embed_resource(resource):
    url = resource.get('author_url')
    if url is None:
        return None

    try:
        return Account.objects.get(service='', ident=url)
    except Account.DoesNotExist:
        pass

    if resource.get('author_name') is None:
        author_url_parts = urlparse(url)
        author_name = '/'.join((author_url_parts.netloc, author_url_parts.path))
    else:
        author_name = resource['author_name']

    # TODO: go find an avatar by way of ~~=<( MAGIC )>=~~
    person = Person(
        display_name=author_name,
    )
    person.save()
    acc = Account(
        service='',
        ident=url,
        display_name=author_name,
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

    h = EmbedlamUserAgent()
    resp, cont = h.request(endpoint_url)
    if resp.status == 404:
        raise RequestError("404 Not Found requesting OEmbed resource %s" % endpoint_url)
    if resp.status == 403:
        raise RequestError("403 Forbidden requesting OEmbed resource %s" % endpoint_url)
    if resp.status == 401:
        raise RequestError("401 Unauthorized requesting OEmbed resource %s" % endpoint_url)
    if resp.status != 200:
        raise ValueError("Unexpected response requesting OEmbed data %s: %d %s" % (endpoint_url, resp.status, resp.reason))
    log.debug('JSON OEmbed endpoint %r returned resource of type %r', endpoint_url, resp['content-type'])

    try:
        resource = json.loads(cont)
    except ValueError, exc:
        log.error("Couldn't decode JSON from OEmbed endpoint %r", endpoint_url, exc_info=exc)
        return

    try:
        resource_type = resource['type']
    except KeyError:
        log.debug("wtf is %r", resource)
        raise RequestError("Resource from OEmbed request %s has no 'type'" % (endpoint_url,))

    if resource_type in ('video', 'rich'):
        obj = Object(
            service='',
            foreign_id=target_url,
            render_mode='mixed',
            title=resource.get('title', ''),
            body=resource.get('html', ''),
            author=account_for_embed_resource(resource),
            time=datetime.utcnow(),
            permalink_url=target_url,
        )
        obj.save()
        return obj
    elif resource_type in ('photo', 'image'):
        image = Media(
            image_url=resource['url'],
            width=resource.get('width'),
            height=resource.get('height'),
        )
        image.save()
        obj = Object(
            service='',
            foreign_id=target_url,
            render_mode='image',
            title=resource.get('title', ''),
            image=image,
            author=account_for_embed_resource(resource),
            time=datetime.utcnow(),
            permalink_url=target_url,
        )
        obj.save()
        return obj
    elif resource_type == 'link':
        obj = Object(
            service='',
            # Even if the resource includes an 'url', we only tested if target_url exists, so keep using it.
            foreign_id=target_url,
            render_mode='link',
            title=resource.get('title', ''),
            body=resource.get('html', ''),
            author=account_for_embed_resource(resource),
            permalink_url=resource.get('url') or target_url,  # might be given anyway
            time=datetime.utcnow(),
        )
        if 'thumbnail_url' in resource:
            image = Media(
                image_url=resource['thumbnail_url'],
                width=resource.get('thumbnail_width'),
                height=resource.get('thumbnail_height'),
            )
            image.save()
            obj.image = image
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

    old_facebook_video_elem = head.find('link', rel='video_src')
    video_url = value_for_meta_elems((old_facebook_video_elem,), base_url=orig_url)

    og_image_elem = head.find("meta", property="og:image")
    old_facebook_image_elem = head.find("link", rel="image_src")
    image_url = value_for_meta_elems((og_image_elem, old_facebook_image_elem), base_url=orig_url)

    og_summary_elem = head.find("meta", property="og:description")
    summary = value_for_meta_elems((og_summary_elem,), "")

    if not video_url and not image_url and not summary:
        log.debug("Found neither an image URL nor a summary for %s, so returning no object", url)
        return None

    image = None
    if video_url:
        embed_code_parts = ["<embed", 'src="%s"' % video_url, 'allowfullscreen="true" wmode="transparent"']

        video_height_elem = head.find('meta', attrs={'name': 'video_height'})
        video_height = value_for_meta_elems((video_height_elem,), '')
        video_width_elem = head.find('meta', attrs={'name': 'video_width'})
        video_width = value_for_meta_elems((video_width_elem,), '')
        video_type_elem = head.find('meta', attrs={'name': 'video_type'})
        video_type = value_for_meta_elems((video_type_elem,), '')

        if video_height:
            embed_code_parts.append('height="%s"' % video_height)
        if video_width:
            embed_code_parts.append('width="%s"' % video_width)

        # Add type and closing bracket always.
        embed_code_parts.append('type="%s">' % (video_type or 'application/x-shockwave-flash'))

        image = Media(
            embed_code=' '.join(embed_code_parts),
            width=int(video_width) if video_width else None,
            height=int(video_height) if video_height else None,
        )
        image.save()
    elif image_url:
        image = Media()
        image.image_url = image_url
        # TODO: how big is this image?
        image.save()

    render_mode = 'link'
    if re.match(r'http://instagr\.am/', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
        render_mode = 'image'
        # Use the same text as the Twitter crosspost for the title.
        if summary and ' at ' in title:
            place = title.split(' at ', 1)[1]
            title = '%s @ %s' % (summary, place)
        elif summary:
            title = summary
        summary = ''
    elif re.match(r'http://yfrog\.com/', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
        render_mode = 'image'
        title = ''
        # TODO: use yfrog xmlInfo call to get the poster's twitter username (if any)

    obj = Object(
        service='',
        foreign_id=url,
        render_mode=render_mode,
        title=title,
        body=summary,
        permalink_url=url,
        time=datetime.utcnow(),
        image=image,
    )
    obj.save()

    return obj


def object_from_feed_entry(feed_url, item_url):
    try:
        feed = feedparser.parse(feed_url)
    except IndexError, exc:
        log.debug("Got a %s parsing feed %s: %s", type(exc).__name__, feed_url, str(exc))
        return None
    matching_entries = [entry for entry in feed.entries if getattr(entry, 'link', None) == item_url]
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
        time=datetime.utcnow(),
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


class RequestError(ValueError):
    pass


class EmbedlamUserAgent(httplib2.Http):

    def __init__(self, cache=None, timeout=10, proxy_info=None):
        super(EmbedlamUserAgent, self).__init__(cache, timeout, proxy_info, disable_ssl_certificate_validation=True)

    def request(self, uri, method='GET', body=None, headers=None, redirections=httplib2.DEFAULT_MAX_REDIRECTS, connection_type=None):
        headers = {} if headers is None else dict(headers)
        headers['user-agent'] = 'leapfrog/1.0'

        # Discover the connection_type ourselves since httplib2 might KeyError doing it.
        if connection_type is None:
            urlparts = urlparse(uri)
            try:
                connection_type = httplib2.SCHEME_TO_CONNECTION[urlparts.scheme]
            except KeyError:
                raise RequestError("Unknown scheme %r for URL %r" % (urlparts.scheme, uri))

        try:
            try:
                resp, cont = super(EmbedlamUserAgent, self).request(uri, method, body, headers, redirections, connection_type)
            except httplib2.FailedToDecompressContent:
                # Try asking again with no compression.
                headers['Accept-Encoding'] = 'identity'
                resp, cont = super(EmbedlamUserAgent, self).request(uri, method, body, headers, redirections, connection_type)
        except socket.timeout:
            raise RequestError("Request to %s timed out" % uri)
        except socket.error, exc:
            raise RequestError("Request to %s could not complete: %s" % (uri, str(exc)))
        except httplib2.RedirectLimit:
            raise RequestError("%s redirected too many times" % uri)
        except httplib2.ServerNotFoundError, exc:
            raise RequestError(str(exc))
        except httplib2.RelativeURIError:
            raise RequestError("httplib2 won't resolve relative URL %r" % uri)
        except httplib.BadStatusLine:
            raise RequestError("%s returned an empty response (probably)" % uri)
        except httplib.IncompleteRead:
            raise RequestError("Got an incomplete read trying to load %s" % uri)
        except httplib.InvalidURL:
            raise RequestError("Invalid URL %r according to httplib" % uri)
        except ssl.SSLError, exc:
            raise RequestError("Error occurred fetching %s over SSL: %s" % (uri, str(exc)))

        if resp.status >= 500:
            raise RequestError("Server Error %d fetching %s", resp.status, uri)

        return resp, cont


class Page(object):

    def __init__(self, url):
        self.content = ''
        self.orig_url = url
        self.url = url
        self.type = 'html'

        # These we can already ask about by URL, so don't bother fetching about them.
        if re.match(r'http:// (?: [^/]* flickr\.com/photos/[^/]+/\d+ | twitpic\.com/\w+ | twitter\.com/ (?: \#!/ )? [^/]+/ status/ (\d+) | vimeo\.com/ \d+ )', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            return

        if re.match(r'http://(?: nyti\.ms | [^.]*\.nytimes\.com )', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
            max_redirects = 10
        else:
            max_redirects = httplib2.DEFAULT_MAX_REDIRECTS

        # Fetch the resource and soupify it.
        h = EmbedlamUserAgent()
        resp, content = h.request(url, redirections=max_redirects)

        if resp.status == 404:
            raise RequestError("404 Not Found discovering %s" % url)
        if resp.status == 403:
            raise RequestError("403 Forbidden discovering %s" % url)
        if resp.status == 401:
            raise RequestError("401 Unauthorized discovering %s" % url)
        if resp.status == 400 and resp.reason == 'BAD_REQUEST' and url.startswith('http://bit.ly/'):
            raise RequestError("Spurious 400 Bad Request from bit.ly requesting %s" % url)
        if resp.status == 429:
            raise RequestError("429 Too Many Requests from bitly (?) requesting %s" % url)
        if resp.status != 200:
            raise ValueError("Unexpected response discovering %s: %d %s" % (url, resp.status, resp.reason))
        url = resp['content-location']

        content_type_str = resp.get('content-type')
        if content_type_str is None or '/' not in content_type_str:
            content_type_str = 'application/x-unknown'

        try:
            major_minor_type = content_type_str.split(';', 1)[0].strip()
            content_type = [x.strip() for x in major_minor_type.split('/', 1)]
        except ValueError:
            raise ValueError("Could not parse purported mime type %r" % content_type_str)

        if content_type[0] == 'image':
            log.debug("This seems to be an image")
            self.type = 'image'
            return

        if major_minor_type not in ('text/html', 'application/xhtml+xml'):
            # hmm
            raise RequestError("Unsupported content type %s/%s for resource %s" % (content_type[0], content_type[1], url))

        try:
            soup = BeautifulSoup(content)
        except HTMLParseError, exc:
            raise ValueError("Could not parse HTML response for %s: %s" % (url, str(exc)))
        head = soup.head
        if head is None:
            raise RequestError('Could not discover against HTML target %s with no head' % url)

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

        xms = re.MULTILINE | re.DOTALL | re.VERBOSE
        if re.match(r'http:// [^/]* flickr\.com/photos/[^/]+/\d+', url, xms):
            return leapfrog.poll.flickr.object_from_url(url)
        if re.match(r'http://twitpic\.com/ \w+ ', url, xms):
            return leapfrog.poll.twitter.object_from_twitpic_url(url)
        if re.match(r'http://twitter\.com/ (?: \#!/ )? [^/]+/ status/ (\d+)', url, xms):
            return leapfrog.poll.twitter.object_from_url(url)
        if re.match(r'http://vimeo\.com/ \d+', url, xms):
            return leapfrog.poll.vimeo.object_from_url(url)
        if re.match(r'http://mlkshk\.com/[rp]/(\w+)', url, xms):
            really_a_share, mlkshk_obj = leapfrog.poll.mlkshk.object_from_url(url)
            return mlkshk_obj

        # If it looks like a Tumblr URL, try asking Tumblr about it.
        if re.match(r'http://[^/]+/post/\d+', url, xms):
            try:
                really_a_share, tumblr_obj = leapfrog.poll.tumblr.object_from_url(url)
            except ValueError:
                # Keep trying the regular way.
                pass
            else:
                return tumblr_obj

        # If the site mentions TypePad, try asking TypePad about it.
        is_typepad_url = re.match(r'http:// .* \.typepad\.com/', url, xms)
        mentions_typepad = lambda: re.search(r'typepad', self.content, re.IGNORECASE | xms)
        if is_typepad_url or mentions_typepad():
            try:
                return leapfrog.poll.typepad.object_from_url(url)
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
            oembed_url = urljoin(url, oembed_node['href'])
            return object_from_oembed(oembed_url, url, discovered=True)

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
    """Returns a saved `leapfrog.models.Object` for the resource at the URL
    ``url``.

    If the resulting object has only a title (neither body content nor a
    representative image), this function will return ``None`` instead of
    an `Object` instance.

    """
    return Page(url).to_object()
