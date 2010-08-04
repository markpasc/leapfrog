from urlparse import urljoin

from django.contrib.sites.models import Site
from django.template import Library
from django.template.defaulttags import url, URLNode


register = Library()


class AbsoluteURLNode(URLNode):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        root = 'http://%s/' % Site.objects.get_current().domain
        return urljoin(root, output)


@register.tag
def absoluteurl(parser, token):
    nodelist = parser.parse(('endabsoluteurl',))
    parser.delete_first_token()
    return AbsoluteURLNode(nodelist)
