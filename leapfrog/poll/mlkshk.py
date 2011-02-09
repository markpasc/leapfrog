import base64
import hashlib
import hmac
import json
import logging
from random import choice
import string
import time
from urlparse import urlparse

import httplib2

from leapfrog.models import Account, Person


log = logging.getLogger(__name__)


def authstring(**kwargs):
    return 'MAC token="%(token)s", timestamp="%(timestamp)s", nonce="%(nonce)s", signature="%(signature)s"' % kwargs


def sign(uri, method, token, secret):
    timestamp = '%d' % time.time()
    nonce = ''.join(choice(string.letters) for x in xrange(10))
    uriparts = urlparse(uri)
    # TODO: use the real port in the signature when the server bug is fixed
    port = '80'
    normalstring = '\n'.join((token, timestamp, nonce, method, uriparts.netloc, port, uriparts.path, uriparts.query))
    log.debug("Mlkshk authentication base string: %r", normalstring)

    log.debug("Mlkshk authentication secret: %r", secret)
    digest = hmac.new(secret, normalstring, hashlib.sha1).digest()
    log.debug("Mlkshk authentication digest: %r", digest)
    signature = base64.encodestring(digest).strip()
    log.debug("Mlkshk base64 auth string: %r", signature)
    return authstring(token=token, nonce=nonce, timestamp=timestamp, signature=signature)


def call_mlkshk(uri, method='GET', body=None, headers=None, authtoken=None, authsecret=None):
    if headers is None:
        headers = {}

    if authtoken is not None:
        headers['Authorization'] = sign(uri, method, authtoken, authsecret)
        log.debug("Mlkshk authentication header: %r", headers['Authorization'])

    h = httplib2.Http()
    resp, cont = h.request(uri, method, body, headers)
    if resp.status != 200:
        raise ValueError("Unexpected HTTP response %d %s requesting %s" % (resp.status, resp.reason, uri))

    try:
        return json.loads(cont)
    except ValueError, exc:
        raise ValueError("Invalid JSON response requesting %s: %s" % (uri, str(exc)))


def account_for_mlkshk_userinfo(userinfo, person=None):
    account_id = str(userinfo['id'])
    try:
        return Account.objects.get(service='mlkshk.com', ident=account_id)
    except Account.DoesNotExist:
        pass

    username = userinfo['name']
    if person is None:
        # TODO: use mlkshk profile images when we get stabler urls for them
        person = Person(
            display_name=username,
            permalink_url='http://mlkshk.com/user/%s' % username,
        )
        person.save()

    account = Account(
        service='mlkshk.com',
        ident=account_id,
        display_name=username,
        person=person,
    )
    account.save()

    return account
