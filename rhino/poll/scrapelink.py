import logging
import urllib2
from rhino.models import Object, Media
from datetime import datetime
from HTMLParser import HTMLParseError
from BeautifulSoup import BeautifulSoup


log = logging.getLogger(__name__)


def object_for_url(url):
    # FIXME: Try OEmbed in here first?

    opener = urllib2.build_opener()
    opener.addheaders = (
        ('User-Agent', 'rhino-scraper'),
    )
    try:
        response = opener.open(url)
    except urllib2.HTTPError:
        return None
    permalink_url = response.geturl()

    headers = response.info()
    try:
        content_type = headers['Content-Type']
    except KeyError:
        logging.debug("%s has no Content-Type header", url)
        return None
    if not 'html' in content_type.lower():
        logging.debug("%s is not HTML", url)
        return None

    try:
        page = BeautifulSoup(response.read())
    except HTMLParseError:
        logging.debug("%s has unparsable HTML", url)
        return None
    head = page.head
    if head is None:
        logging.debug("%s has no head element", url)
        return None

    title = ""
    # Try a number of strategies to extract a title
    og_title_elem = head.find("meta", property="og:title")
    old_facebook_title_elem = head.find("meta", {"name":"title"})
    title_elem = head.find("title")
    if og_title_elem:
        title = og_title_elem["content"]
    elif old_facebook_title_elem:
        title = old_facebook_title_elem["content"]
    elif title_elem:
        title = title_elem.string

    image_url = None
    og_image_elem = head.find("meta", property="og:image")
    old_facebook_image_elem = head.find("link", rel="image_src")
    if og_image_elem:
        image_url = og_image_elem["content"]
    elif old_facebook_image_elem:
        image_url = old_facebook_image_elem["href"]

    og_url_elem = head.find("meta", property="og:url")
    if og_url_elem:
        og_url = og_url_elem["content"]
        # Only allow this canonicalization if it's a prefix
        # of the original URL.
        if permalink_url.startswith(og_url):
            permalink_url = og_url

    summary = ""
    og_summary_elem = head.find("meta", property="og:description")
    if og_summary_elem:
        summary = og_summary_elem["content"]

    image = None
    if image_url:
        image = Media()
        image.image_url = image_url
        image.save()

    obj = Object()
    obj.service = ""
    obj.foreign_id = ""
    obj.title = title
    obj.body = summary
    obj.render_mode = "link"
    obj.time = datetime.today()
    obj.image = image
    obj.permalink_url = permalink_url
    obj.save()

    # Should actually do something here
    return obj


