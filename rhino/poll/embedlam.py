from datetime import datetime
import feedparser
from HTMLParser import HTMLParseError
import json
import logging
import re
from urllib import urlencode
from urlparse import urlparse, urljoin

from BeautifulSoup import BeautifulSoup
import httplib2
from mimeparse import parse_mime_type

from rhino.models import Account, Object, Person, Media
import rhino.poll.twitter


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

    resource_type = resource['type']
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
    elif resource_type == 'photo':
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


def object_from_html_head(url, orig_url, head):

    # Try a number of strategies to extract a title.
    og_title_elem = head.find("meta", property="og:title")
    old_facebook_title_elem = head.find("meta", {"name":"title"})
    title_elem = head.find("title")
    title = value_for_meta_elems((og_title_elem, old_facebook_title_elem, title_elem), "")

    og_image_elem = head.find("meta", property="og:image")
    old_facebook_image_elem = head.find("link", rel="image_src")
    image_url = value_for_meta_elems((og_image_elem, old_facebook_image_elem), base_url=orig_url)

    og_summary_elem = head.find("meta", property="og:description")
    summary_elem = head.find('meta', {'name': 'description'})
    summary = value_for_meta_elems((og_summary_elem, summary_elem), "")

    image = None
    if image_url:
        image = Media()
        image.image_url = image_url
        image.save()

    obj = Object(
        service='',
        foreign_id=url,
        render_mode='link',
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

    object_time = entry.published_parsed if "published_parsed" in entry else entry.updated_parsed;
    if object_time:
        obj.time = datetime(*object_time[:6])

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

        if value is not None:
            if base_url:
                return urljoin(base_url, value)
            else:
                return value

    return default


def object_for_url(url):
    # Is this a special URL we have a special handler for?
    # TODO: special handlers
    if re.match(r'http:// .* \.flickr\.com/', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
        return object_from_oembed('http://www.flickr.com/services/oembed/', url)
    if re.match(r'http://twitpic\.com/ \w+ ', url, re.MULTILINE | re.DOTALL | re.VERBOSE):
        return rhino.poll.twitter.object_from_twitpic_url(url)

    # Fetch the resource and soupify it.
    h = httplib2.Http()
    try:
        resp, content = h.request(url, headers={'User-Agent': 'rhino/1.0'})
    except httplib2.RedirectLimit:
        raise ValueError("%s redirected too many times" % url)
    if resp.status != 200:
        raise ValueError("Unexpected response discovering %s: %d %s" % (url, resp.status, resp.reason))
    url = resp['content-location']

    content_type = parse_mime_type(resp['content-type'])
    if content_type[0:2] != ('text', 'html'):
        # hmm
        raise ValueError("Unsupported content type %s/%s for resource %s" % (content_type[0], content_type[1], url))

    try:
        page = BeautifulSoup(content)
    except HTMLParseError, exc:
        raise ValueError("Could not parse HTML response for %s: %s" % (url, str(exc)))
    head = page.head
    if head is None:
        raise ValueError('Could not discover against HTML target %s with no head' % url)

    # What's the real URL?
    orig_url = url
    canon_url = None
    og_url_elem = head.find("meta", property="og:url")
    canon_elem = head.find('link', rel='canonical')
    canon_url = value_for_meta_elems((og_url_elem, canon_elem), base_url=orig_url)

    if canon_url is not None:
        # Only allow this canonicalization if it's at the same domain as the original URL.
        orig_host = urlparse(url)[1]
        canon_host = urlparse(canon_url)[1]
        if orig_host == canon_host:
            url = canon_url

    try:
        return Object.objects.get(service='', foreign_id=url)
    except Object.DoesNotExist:
        pass  # time to make the donuts

    # Does it support OEmbed?
    oembed_node = head.find(rel='alternate', type='application/json+oembed')
    # TODO: support xml?
    if oembed_node is not None:
        return object_from_oembed(oembed_node['href'], url, discovered=True)

    # Does it have a feed declared? If so, let's go hunting in the feed for
    # an entry corresponding to this page.
    atom_feed_link = head.find(rel='alternate', type='application/atom+xml')
    rss_feed_link = head.find(rel='alternate', type='application/rss+xml')
    feed_url = value_for_meta_elems((atom_feed_link, rss_feed_link), base_url=orig_url)
    if feed_url:
        object = object_from_feed_entry(feed_url, url)
        if object:
            return object

    return object_from_html_head(url, orig_url, head)
