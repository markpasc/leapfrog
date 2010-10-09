import logging
import urllib2

log = logging.getLogger(__name__)

def object_for_url(url):
    # FIXME: Try OEmbed in here first?

    opener = urllib2.build_opener()
    opener.addheaders = (
        ('User-Agent', 'rhino-scraper'),
    )
    response = opener.open(url)
    permalink_url = response.geturl()

    headers = response.info()
    try:
        content_type = headers['Content-Type']
    except KeyError:
        return None
    if not 'html' in content_type.lower():
        return None

    try:
        page = BeautifulSoup(response.read())
    except HTMLParseError:
        return None
    head = page.head
    if head is None:
        return None

    # Should actually do something here
    return None


