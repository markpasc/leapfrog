from datetime import datetime
from HTMLParser import HTMLParseError
import logging
import urllib2

from BeautifulSoup import BeautifulSoup
import oembed
from oembed import Consumer as OEmbedConsumer
from oembed import Endpoint as OEmbedEndpoint
from oembed import Error as OEmbedError
#from oembed import OEmbedConsumer, OEmbedEndpoint, OEmbedError

from rhino.models import Account, Object, Person


log = logging.getLogger(__name__)


class DiscoveredEndpoint(OEmbedEndpoint):

    def request(self, url, **opt):
        # We already used the url to find our endpoint URL, so don't add more query args again.
        return self._urlApi


class DiscoveryConsumer(OEmbedConsumer):

    def find_endpoint(self, url):
        endpoint = super(DiscoveryConsumer, self).find_endpoint(url)
        if endpoint is None:
            endpoint = self.discoverEndpoint(url)
        return endpoint

    def discoverEndpoint(self, url):
        opener = urllib2.build_opener()
        opener.addheaders = (
            ('User-Agent', 'python-oembed/whatever'),
        )
        response = opener.open(url)
        log.debug('To find out about %s, ended up discovering against %s', url, response.geturl())
        url = self.last_real_url = response.geturl()

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
    csr.add_provider('http://www.flickr.com/services/oembed',
        ['http://*.flickr.com/*', 'http://flic.kr/*'])

    try:
        resource = csr.lookup(url)
    except (OEmbedError, urllib2.HTTPError), exc:
        raise EmbedError('%s trying to embed %s: %s' % (type(exc).__name__, url, str(exc)))

    # well
    log.debug('YAY OEMBED ABOUT %s: %r', url, resource.getData())

    return csr.last_real_url, resource


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


def object_for_embed(url):
    real_url, resource = embed(url)

    try:
        return Object.objects.get(service='', foreign_id=real_url)
    except Object.DoesNotExist:
        pass

    resource_type = resource['type']
    if resource_type == 'video':
        obj = Object(
            service='',
            foreign_id=real_url,
            render_mode='mixed',
            title=resource['title'],
            body=resource['html'],
            author=account_for_embed_resource(resource),
            time=datetime.now(),
            permalink_url=real_url,
        )
        obj.save()
        return obj

    raise EmbedError('Unknown embed resource type %r' % resource_type)
