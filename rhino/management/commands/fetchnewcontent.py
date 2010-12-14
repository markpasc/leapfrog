from datetime import datetime, timedelta
import logging
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError
from sentry.client.base import SentryClient

from rhino.models import *
from rhino.poll import twitter
from rhino.poll import typepad
from rhino.poll import flickr
from rhino.poll import facebook
from rhino.poll import vimeo
from rhino.poll import tumblr


pollers = {
    'facebook.com': facebook.poll_facebook,
    'flickr.com': flickr.poll_flickr,
    'tumblr.com': tumblr.poll_tumblr,
    'twitter.com': twitter.poll_twitter,
    'typepad.com': typepad.poll_typepad,
    'vimeo.com': vimeo.poll_vimeo,
}


class Command(NoArgsCommand):

    option_list = NoArgsCommand.option_list + (
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='Update all accounts, even ones that have been updated recently',
        ),
    )

    def fetch_new_content(self, **options):
        update_horizon = datetime.now() - timedelta(minutes=15)

        users = User.objects.all()
        for user in users:
            try:
                person = user.person
            except Person.DoesNotExist:
                continue

            for account in person.accounts.all():
                log = logging.getLogger('%s.%s' % (__name__, account.service))

                try:
                    poller = pollers[account.service]
                except KeyError:
                    log.debug("Account service %s has no poller, skipping", account.service)
                    continue

                if not options['force'] and account.last_updated > update_horizon:
                    log.debug("Account %s %s was updated fewer than 15 minutes ago, skipping", account.service, account.display_name)
                    continue

                # Mark the account as updated even if the update fails later.
                log.debug("Polling account %s %s", account.service, account.display_name)
                account.last_updated = datetime.now()
                account.save()

                try:
                    poller(account)
                except Exception, exc:
                    SentryClient().create_from_exception(view='%s.%s' % (__name__, account.service))
                    #log.exception(exc)

    def handle_noargs(self, **options):
        try:
            self.fetch_new_content(**options)
        except Exception, exc:
            SentryClient().create_from_exception(view=__name__)
