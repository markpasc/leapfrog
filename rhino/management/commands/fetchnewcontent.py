from django.core.management.base import NoArgsCommand, CommandError

from rhino.models import *
from rhino.poll import twitter
from rhino.poll import typepad


pollers = {
    "twitter.com": twitter.poll_twitter,
    "typepad.com": typepad.poll_typepad,
}


class Command(NoArgsCommand):

    def handle_noargs(self, **options):
        users = User.objects.all()
        for user in users:
            try:
                for account in user.person.accounts.all():
                    if account.service in pollers:
                        poller = pollers[account.service]
                        poller(account)
            except Person.DoesNotExist:
                pass
