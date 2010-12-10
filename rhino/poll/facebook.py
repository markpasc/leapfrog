from datetime import datetime
import json
import logging
import re

from django.conf import settings
import httplib2
import oauth2 as oauth

from rhino.models import Object, Account, Person, UserStream, Media, UserReplyStream
import rhino.poll.embedlam


log = logging.getLogger(__name__)


def poll_facebook(account):
    user = account.person.user
    if user is None:
        return

    # not yet implemented
    raise Exception("Polling facebook is not implemented yet")


def account_for_facebook_user(fb_user, person=None):
    try:
        account = Account.objects.get(service='facebook.com', ident=fb_user["id"])
    except Account.DoesNotExist:
        if person is None:
            avatar = Media(
                width=50,
                height=50,
                image_url='http://graph.facebook.com/%i/picture' % fb_user["id"]
            )
            avatar.save()
            person = Person(
                display_name=fb_user["name"],
                avatar=avatar,
                permalink_url=fb_user["link"],
            )
            person.save()
        account = Account(
            service='facebook.com',
            ident=fb_user["id"],
            display_name=fb_user["name"],
            person=person,
        )
        account.save()

    return account
