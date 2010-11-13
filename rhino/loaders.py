"""
See http://docs.djangoproject.com/en/dev/ref/templates/api/#using-an-alternative-template-language

Use:
 * {{ url_for('view_name') }} instead of {% url view_name %},
 * <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
   instead of {% csrf_token %}.

"""

from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import TemplateDoesNotExist
from django.template.loader import BaseLoader
from django.template.loaders.app_directories import app_template_dirs
import jinja2


class Template(jinja2.Template):

    def render(self, context):
        # flatten the Django Context into a single dictionary.
        context_dict = {}
        for d in context.dicts:
            context_dict.update(d)
        return super(Template, self).render(context_dict)


def url_for(name, *args, **kwargs):
    return reverse(name, args=args, kwargs=kwargs)


class Loader(BaseLoader):

    is_usable = True

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(app_template_dirs))
    env.template_class = Template

    # These are available to all templates.
    env.globals['url_for'] = url_for
    env.globals['MEDIA_URL'] = settings.MEDIA_URL

    def load_template(self, template_name, template_dirs=None):
        if not template_name.endswith('.jj'):
            raise TemplateDoesNotExist(template_name)
        try:
            template = self.env.get_template(template_name)
        except jinja2.TemplateNotFound:
            raise TemplateDoesNotExist(template_name)
        return template, template.filename
