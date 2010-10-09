from django.core.management.base import BaseCommand, CommandError
from rhino.models import *

from rhino.poll import scrapelink

class Command(BaseCommand):

    def handle(self, *args, **options):
        url = args[0]
        obj = scrapelink.object_for_url(url)

        if obj:
            print "Created " + repr(obj)
        else:
            print "Failed to create an object for that URL"

