import logging

from django.core.management.base import NoArgsCommand, CommandError

from rhino.models import *
from rhino.poll import twitter
from rhino.poll import typepad
from rhino.poll import flickr


pollers = {
    "twitter.com": twitter.poll_twitter,
    "typepad.com": typepad.poll_typepad,
    "flickr.com": flickr.poll_flickr,
}


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        users = User.objects.all()
        for user in users:
            try:
                person = user.person
            except Person.DoesNotExist:
                continue

            for account in person.accounts.all():
                if account.service not in pollers:
                    continue

                poller = pollers[account.service]
                try:
                    poller(account)
                except Exception, exc:
                    log = logging.getLogger('%s.%s' % (__name__, account.service))
                    log.exception(exc)
