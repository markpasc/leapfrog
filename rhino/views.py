import json
import logging
from random import choice
import string
from urllib import urlencode, quote
from urlparse import parse_qsl, urlunparse

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
import httplib2
import oauth2 as oauth
import typd.objecttypes

from rhino.poll.twitter import account_for_twitter_user
from rhino.poll.typepad import account_for_typepad_user
from rhino.poll.flickr import sign_flickr_query, account_for_flickr_id, call_flickr


log = logging.getLogger(__name__)


class LoginUrl(object):
    def __str__(self):
        try:
            return self.url
        except AttributeError:
            self.url = reverse('signin')
            return self.url


@login_required(login_url=LoginUrl())
def home(request):
    user = request.user

    stream_items = user.stream_items.order_by("-time").select_related()
    stream_items = list(stream_items[:50])

    # Put the stream items' replies on the items.
    try:
        first_stream_item, last_stream_item = stream_items[0], stream_items[-1]
    except IndexError:
        # No stream items?
        pass
    else:
        replies = user.reply_stream_items.filter(root_time__range=(last_stream_item.time, first_stream_item.time)).select_related()
        reply_by_item = dict()
        for reply in replies:
            item_replies = reply_by_item.setdefault(reply.root_id, set())
            item_replies.add(reply)
            log.debug("Saving reply #%d %r for obj #%d", reply.pk, reply, reply.root_id)
        for item in stream_items:
            reply_set = reply_by_item.get(item.obj_id, set())
            item.replies = sorted(iter(reply_set), key=lambda i: i.reply_time)
            log.debug("Found %d replies for obj #%d %s", len(item.replies), item.obj_id, item.obj.title)

    data = {
        'stream_items': stream_items,
        'page_title': "%s's neighborhood" % user.person.display_name,
    }

    template = 'rhino/index.jj'
    return render_to_response(template, data,
        context_instance=RequestContext(request))


def signin_twitter(request):
    csr = oauth.Consumer(*settings.TWITTER_CONSUMER)
    client = oauth.Client(csr)

    oauth_callback = quote(request.build_absolute_uri(reverse('complete-twitter')))
    resp, content = client.request('https://api.twitter.com/oauth/request_token?oauth_callback=%s' % oauth_callback)
    if resp.status != 200:
        raise ValueError("Unexpected response asking for request token: %d %s" % (resp.status, resp.reason))

    request_token = dict(parse_qsl(content))
    request.session['twitter_request_token'] = request_token

    return HttpResponseRedirect('https://api.twitter.com/oauth/authenticate?oauth_token=%s' % request_token['oauth_token'])


def complete_twitter(request):
    try:
        request_token = request.session['twitter_request_token']
    except KeyError:
        raise ValueError("Can't complete Twitter authentication without a request token for this session")

    try:
        verifier = request.GET['oauth_verifier']
    except KeyError:
        raise ValueError("Can't complete Twitter authentication without a verifier")

    csr = oauth.Consumer(*settings.TWITTER_CONSUMER)
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
    client = oauth.Client(csr, token)

    body = urlencode({'oauth_verifier': verifier})
    resp, content = client.request('https://api.twitter.com/oauth/access_token', method='POST', body=body)
    if resp.status != 200:
        raise ValueError("Unexpected response exchanging for access token: %d %s" % (resp.status, resp.content))

    access_token = dict(parse_qsl(content))
    del request.session['twitter_request_token']
    #request.session['access_token'] = access_token

    # But who is that?
    client = oauth.Client(csr, oauth.Token(access_token['oauth_token'], access_token['oauth_token_secret']))
    resp, content = client.request('https://api.twitter.com/1/account/verify_credentials.json')
    if resp.status != 200:
        raise ValueError("Unexpected response verifying credentials: %d %s" % (resp.status, resp.reason))

    userdata = json.loads(content)

    person = None
    if not request.user.is_anonymous():
        person = request.user.person
    account = account_for_twitter_user(userdata, person=person)
    if request.user.is_anonymous():
        person = account.person
        if person.user is None:
            # AGH
            random_name = ''.join(choice(string.letters + string.digits) for i in range(20))
            while User.objects.filter(username=random_name).exists():
                random_name = ''.join(choice(string.letters + string.digits) for i in range(20))
            person.user = User.objects.create_user(random_name, '%s@example.com' % random_name)
            person.save()

        person.user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, person.user)

    account.authinfo = ':'.join((access_token['oauth_token'], access_token['oauth_token_secret']))
    account.save()

    return HttpResponseRedirect(reverse('home'))


def signin_typepad(request):
    csr = oauth.Consumer(*settings.TYPEPAD_CONSUMER)
    client = oauth.Client(csr)

    oauth_callback = quote(request.build_absolute_uri(reverse('complete-typepad')))
    resp, content = client.request('https://www.typepad.com/secure/services/oauth/request_token?oauth_callback=%s' % oauth_callback)
    if resp.status != 200:
        raise ValueError('Unexpected response asking for TypePad request token: %d %s' % (resp.status, resp.reason))

    request_token = dict(parse_qsl(content))
    request.session['typepad_request_token'] = request_token

    return HttpResponseRedirect('https://www.typepad.com/secure/services/api/6p0120a96c7944970b/oauth-approve?oauth_token=%s' % request_token['oauth_token'])


def complete_typepad(request):
    try:
        request_token = request.session['typepad_request_token']
    except KeyError:
        raise ValueError("Can't complete TypePad authentication without a request token in the session")

    try:
        verifier = request.GET['oauth_verifier']
    except KeyError:
        raise ValueError("Can't complete TypePad authentication without a verifier")

    csr = oauth.Consumer(*settings.TYPEPAD_CONSUMER)
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
    client = oauth.Client(csr, token)

    body = urlencode({'oauth_verifier': verifier})
    resp, content = client.request('https://www.typepad.com/secure/services/oauth/access_token', method='POST', body=body)
    if resp.status != 200:
        raise ValueError("Unexpected response exchanging for access token: %d %s" % (resp.status, resp.reason))

    access_token_data = dict(parse_qsl(content))
    del request.session['typepad_request_token']

    # But who is it?
    access_token = oauth.Token(access_token_data['oauth_token'], access_token_data['oauth_token_secret'])
    oauth_request = oauth.Request.from_consumer_and_token(csr, access_token,
        http_method='GET', http_url='https://api.typepad.com/users/@self.json')
    oauth_sign_method = oauth.SignatureMethod_HMAC_SHA1()
    oauth_request.sign_request(oauth_sign_method, csr, access_token)
    oauth_signing_base = oauth_sign_method.signing_base(oauth_request, csr, access_token)
    oauth_header = oauth_request.to_header()
    h = httplib2.Http()
    h.follow_redirects = 0
    resp, content = h.request(oauth_request.normalized_url, method=oauth_request.method,
        headers=oauth_header)
    if resp.status != 302:
        raise ValueError("Unexpected response verifying TypePad credentials: %d %s" % (resp.status, resp.reason))

    userdata = json.loads(content)
    tp_user = typd.objecttypes.User.from_dict(userdata)

    person = None
    if not request.user.is_anonymous():
        person = request.user.person
    account = account_for_typepad_user(tp_user, person=person)
    if request.user.is_anonymous():
        person = account.person
        if person.user is None:
            # AGH
            random_name = ''.join(choice(string.letters + string.digits) for i in range(20))
            while User.objects.filter(username=random_name).exists():
                random_name = ''.join(choice(string.letters + string.digits) for i in range(20))
            person.user = User.objects.create_user(random_name, '%s@example.com' % random_name)
            person.save()

        person.user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, person.user)

    account.authinfo = ':'.join((access_token_data['oauth_token'], access_token_data['oauth_token_secret']))
    account.save()

    return HttpResponseRedirect(reverse('home'))


def signin_flickr(request):
    query = {
        'api_key': settings.FLICKR_KEY[0],
        'perms': 'read',
    }
    sign_flickr_query(query)
    url = urlunparse(('http', 'flickr.com', 'services/auth/', None, urlencode(query), None))

    return HttpResponseRedirect(url)


def complete_flickr(request):
    try:
        frob = request.GET['frob']
    except KeyError:
        raise ValueError("Redirect back from Flickr did not include a frob")

    result = call_flickr('flickr.auth.getToken', sign=True, frob=frob)

    try:
        nsid = result['auth']['user']['nsid']
    except KeyError:
        raise ValueError("Result of Flickr getToken call did not have a user NSID")

    try:
        token = result['auth']['token']['_content']
    except KeyError:
        raise ValueError("Result of Flickr getToken call did not include a token")

    person = None
    if not request.user.is_anonymous():
        person = request.user.person
    account = account_for_flickr_id(nsid, person=person)
    if request.user.is_anonymous():
        person = account.person
        if person.user is None:
            random_name = ''.join(choice(string.letters + string.digits) for i in range(20))
            while User.objects.filter(username=random_name).exists():
                random_name = ''.join(choice(string.letters + string.digits) for i in range(20))
            person.user = User.objects.create_user(random_name, '%s@example.com' % random_name)
            person.save()

    account.authinfo = token
    account.save()

    return HttpResponseRedirect(reverse('home'))


def redirect_home(request):
    return HttpResponseRedirect(reverse('home'))

