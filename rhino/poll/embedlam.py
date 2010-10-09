from HTMLParser import HTMLParseError
import logging
import urllib2

from BeautifulSoup import BeautifulSoup
import oembed
from oembed import OEmbedConsumer, OEmbedEndpoint, OEmbedError


log = logging.getLogger(__name__)


class DiscoveredEndpoint(OEmbedEndpoint):

    def request(self, url, **opt):
        # We already used the url to find our endpoint URL, so don't add more query args again.
        return self._urlApi


class DiscoveryConsumer(OEmbedConsumer):

    def _endpointFor(self, url):
        endpoint = super(DiscoveryConsumer, self)._endpointFor(url)
        if endpoint is None:
            endpoint = self.discoverEndpoint(url)
        return endpoint

    def discoverEndpoint(self, url):
        opener = urllib2.build_opener()
        opener.addheaders = (
            ('User-Agent', 'python-oembed/' + oembed.__version__),
        )
        response = opener.open(url)
        log.debug('To find out about %s, ended up discovering against %s', url, response.geturl())
        url = response.geturl()

        headers = response.info()
        try:
            content_type = headers['Content-Type']
        except KeyError:
            raise OEmbedError('Resource targeted for discovery has no Content Type')
        if not 'html' in content_type.lower():
            raise OEmbedError('Resource targeted for discovery is %s, not an HTML page' % content_type)

        try:
            page = BeautifulSoup(response.read())
        except HTMLParseError:
            raise OEmbedError('Could not discover against invalid HTML target %s' % url)
        head = page.head
        if head is None:
            raise OEmbedError('Could not discover against HTML target %s with no head' % url)

        oembed_node = head.find(rel='alternate', type='application/json+oembed')
        if oembed_node is None:
            oembed_node = head.find(rel='alternate', type='text/xml+oembed')
        if oembed_node is None:
            raise OEmbedError('Could not discover against HTML target %s with no oembed tags' % url)

        return DiscoveredEndpoint(oembed_node['href'])


class EmbedError(Exception):
    pass


def embed(url):
    csr = DiscoveryConsumer()
    endp = OEmbedEndpoint('http://www.flickr.com/services/oembed',
        ['http://*.flickr.com/*', 'http://flic.kr/*'])
    csr.addEndpoint(endp)

    try:
        resource = csr.embed(url)
    except (OEmbedError, urllib2.HTTPError), exc:
        raise EmbedError('%s trying to embed %s: %s' % (type(exc).__name__, url, str(exc)))

    # well
    log.debug('YAY OEMBED ABOUT %s: %r', url, resource.getData())

    return resource
