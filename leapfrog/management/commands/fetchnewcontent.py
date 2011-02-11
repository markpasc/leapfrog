from datetime import datetime, timedelta
import logging
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError
from sentry.client.base import SentryClient

from leapfrog.models import *
from leapfrog.poll import facebook
from leapfrog.poll import flickr
from leapfrog.poll import mlkshk
from leapfrog.poll import tumblr
from leapfrog.poll import twitter
from leapfrog.poll import typepad
from leapfrog.poll import vimeo


pollers = {
    'facebook.com': facebook.poll_facebook,
    'flickr.com': flickr.poll_flickr,
    'mlkshk.com': mlkshk.poll_mlkshk,
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
        last_viewed_horizon = datetime.now() - timedelta(days=5)

        users = User.objects.all()
        for user in users:
            try:
                person = user.person
            except Person.DoesNotExist:
                continue

            # Don't update accounts if someone hasn't viewed the site in some days.
            if person.last_viewed_home < last_viewed_horizon:
                logging.getLogger(__name__).debug("User %s hasn't viewed the site in a while; skipping", user.username)
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
                    log.exception(exc)
                    SentryClient().create_from_exception(view='%s.%s' % (__name__, account.service))
                else:
                    account.last_success = datetime.now()
                    account.save()

    def handle_noargs(self, **options):
        try:
            self.fetch_new_content(**options)
        except Exception, exc:
            log.exception(exc)
            SentryClient().create_from_exception(view=__name__)
