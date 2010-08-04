from django.template import Library
from django.template.defaulttags import url, URLNode


register = Library()


class AbsoluteURLNode(URLNode):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        return context['request'].build_absolute_uri(output)


@register.tag
def absoluteurl(parser, token):
    nodelist = parser.parse(('endabsoluteurl',))
    parser.delete_first_token()
    return AbsoluteURLNode(nodelist)
