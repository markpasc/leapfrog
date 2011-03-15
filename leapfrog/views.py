from base64 import b64encode
from datetime import datetime
import json
import logging
from random import choice
import string
from urllib import urlencode, quote
from urlparse import parse_qsl, parse_qs, urlparse, urlunparse
from xml.etree import ElementTree

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import render_to_string
import httplib2
import oauth2 as oauth
import typd.objecttypes

from leapfrog.models import Person, Account, UserSetting, Object
from leapfrog.poll.facebook import account_for_facebook_user
from leapfrog.poll.flickr import sign_flickr_query, account_for_flickr_id, call_flickr
from leapfrog.poll.mlkshk import account_for_mlkshk_userinfo, call_mlkshk
from leapfrog.poll.tumblr import account_for_tumblelog_element
from leapfrog.poll.twitter import account_for_twitter_user
from leapfrog.poll.typepad import account_for_typepad_user
from leapfrog.poll.vimeo import account_for_vimeo_id, call_vimeo


log = logging.getLogger(__name__)


def stream_items_for_user(user, before=None, after=None, limit=20):
    stream_items = user.stream_items
    if before is not None:
        stream_items = stream_items.filter(time__lte=before)
    elif after is not None:
        stream_items = stream_items.filter(time__gte=after)
    stream_items = stream_items.order_by("-time").select_related()
    stream_items = list(stream_items[:limit])

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

    return stream_items


@login_required()
def home(request):
    user = request.user
    try:
        person = user.person
    except Person.DoesNotExist:
        display_name = user.get_full_name()
        accounts = {}
    else:
        display_name = person.display_name
        accounts = dict((acc.service, acc) for acc in person.accounts.all() if acc.authinfo)

        person.last_viewed_home = datetime.utcnow()
        person.save()

    stream_items = stream_items_for_user(user)
    try:
        pagecolor_obj = UserSetting.objects.get(user=user, key='pagecolor')
    except UserSetting.DoesNotExist:
        pagecolor = 'orange'
    else:
        pagecolor = pagecolor_obj.value

    try:
        maxstreamitem = request.user.stream_items.values_list('id', flat=True).order_by('-id')[0]
    except IndexError:
        maxstreamitem = 0
    try:
        maxreplyitem = request.user.reply_stream_items.values_list('id', flat=True).order_by('-id')[0]
    except IndexError:
        maxreplyitem = 0

    data = {
        'stream_items': stream_items,
        'page_title': "%s's neighborhood" % display_name,
        'accounts': accounts,
        'pagecolor': pagecolor,
        'maxstreamitem': maxstreamitem,
        'maxreplyitem': maxreplyitem,
    }

    template = 'leapfrog/index.jj'
    return render_to_response(template, data,
        context_instance=RequestContext(request))


@login_required()
def mobile_home(request):
    user = request.user
    try:
        person = user.person
    except Person.DoesNotExist:
        display_name = user.get_full_name()
    else:
        display_name = person.display_name

        person.last_viewed_home = datetime.utcnow()
        person.save()

    try:
        pagecolor_obj = UserSetting.objects.get(user=user, key='pagecolor')
    except UserSetting.DoesNotExist:
        pagecolor = 'orange'
    else:
        pagecolor = pagecolor_obj.value

    data = {
        'page_title': "%s's neighborhood" % display_name,
        'pagecolor': pagecolor,
    }

    template = 'leapfrog/mobile_index.jj'
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

    return HttpResponseRedirect('https://api.twitter.com/oauth/authorize?oauth_token=%s&oauth_access_type=write' % request_token['oauth_token'])


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
        raise ValueError("Unexpected response exchanging for access token: %d %s" % (resp.status, resp.reason))

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
    else:
        # If the account already existed (because some other user follows
        # that account and had imported objects by them, say), "merge" it
        # onto the signed-in user. (This does mean you can intentionally
        # move an account by signing in as a different django User and re-
        # associating that account, but that's appropriate.)
        account.person = person

    log.debug('Updating authinfo for Twitter account %s to have token %s : %s', account.display_name, access_token['oauth_token'], access_token['oauth_token_secret'])
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

    return HttpResponseRedirect('https://www.typepad.com/secure/services/api/%s/oauth-approve?oauth_token=%s' % (settings.TYPEPAD_APPLICATION, request_token['oauth_token']))


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
    else:
        # If the account already existed (because some other user follows
        # that account and had imported objects by them, say), "merge" it
        # onto the signed-in user. (This does mean you can intentionally
        # move an account by signing in as a different django User and re-
        # associating that account, but that's appropriate.)
        account.person = person

    account.authinfo = ':'.join((access_token_data['oauth_token'], access_token_data['oauth_token_secret']))
    account.save()

    return HttpResponseRedirect(reverse('home'))


def signin_facebook(request):
    redirect_uri = request.build_absolute_uri(reverse('complete-facebook'))

    query = {
        'client_id': settings.FACEBOOK_CONSUMER[0],
        'redirect_uri': redirect_uri,
        'scope': 'read_stream,offline_access',
    }

    url = urlunparse(('http', 'graph.facebook.com', 'oauth/authorize', None, urlencode(query), None))

    return HttpResponseRedirect(url)


def complete_facebook(request):
    redirect_uri = request.build_absolute_uri(reverse('complete-facebook'))
    try:
        code = request.GET["code"]
    except KeyError:
        # Guess they cancelled. That's cool.
        return HttpResponseRedirect(reverse('home'))

    query = {
        'client_id': settings.FACEBOOK_CONSUMER[0],
        'redirect_uri': redirect_uri,
        'code': code,
        'client_secret': settings.FACEBOOK_CONSUMER[1],
    }

    url = urlunparse(('https', 'graph.facebook.com', 'oauth/access_token', None, urlencode(query), None))
    h = httplib2.Http()
    resp, content = h.request(url, method='GET')
    # response is urlencoded
    data = parse_qs(content)
    access_token = data["access_token"][0]

    # Now find out who this user is
    me_query = { 'access_token': access_token }
    me_url = urlunparse(('https', 'graph.facebook.com', 'me', None, urlencode(me_query), None))
    resp, content = h.request(me_url, method='GET')
    fb_user = json.loads(content)

    if "error" in fb_user:
        raise Exception("Facebook returned %s: %s" % (fb_user["error"]["type"], fb_user["error"]["message"]))

    person = None
    if not request.user.is_anonymous():
        person = request.user.person
    account = account_for_facebook_user(fb_user, person=person)
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
    else:
        # If the account already existed (because some other user follows
        # that account and had imported objects by them, say), "merge" it
        # onto the signed-in user. (This does mean you can intentionally
        # move an account by signing in as a different django User and re-
        # associating that account, but that's appropriate.)
        account.person = person

    account.authinfo = access_token
    account.save()

    return HttpResponseRedirect(reverse('home'))


def signin_flickr(request):
    query = {
        'api_key': settings.FLICKR_KEY[0],
        'perms': 'write',
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

        person.user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, person.user)
    else:
        # If the account already existed (because some other user follows
        # that account and had imported objects by them, say), "merge" it
        # onto the signed-in user. (This does mean you can intentionally
        # move an account by signing in as a different django User and re-
        # associating that account, but that's appropriate.)
        account.person = person

    account.authinfo = token
    account.save()

    return HttpResponseRedirect(reverse('home'))


def signin_vimeo(request):
    csr = oauth.Consumer(*settings.VIMEO_CONSUMER)
    client = oauth.Client(csr)

    oauth_callback = quote(request.build_absolute_uri(reverse('complete-vimeo')))
    resp, content = client.request('http://vimeo.com/oauth/request_token?oauth_callback=%s' % oauth_callback)
    if resp.status != 200:
        raise ValueError('Unexpected response asking for Vimeo request token: %d %s' % (resp.status, resp.reason))

    request_token = dict(parse_qsl(content))
    request.session['vimeo_request_token'] = request_token

    return HttpResponseRedirect('http://vimeo.com/oauth/authorize?oauth_token=%s&permission=write' % (request_token['oauth_token'],))


def complete_vimeo(request):
    try:
        request_token = request.session['vimeo_request_token']
    except KeyError:
        raise ValueError("Can't complete Vimeo authentication without a request token in the session")

    try:
        verifier = request.GET['oauth_verifier']
    except KeyError:
        raise ValueError("Can't complete Vimeo authentication without a verifier")

    csr = oauth.Consumer(*settings.VIMEO_CONSUMER)
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
    client = oauth.Client(csr, token)

    body = urlencode({'oauth_verifier': verifier})
    resp, content = client.request('http://vimeo.com/oauth/access_token?oauth_verifier=%s' % verifier)
    if resp.status != 200:
        raise ValueError("Unexpected response exchanging for access token: %d %s" % (resp.status, resp.reason))

    access_token_data = dict(parse_qsl(content))
    del request.session['vimeo_request_token']

    # But who is it?
    access_token = oauth.Token(access_token_data['oauth_token'], access_token_data['oauth_token_secret'])
    userdata = call_vimeo('vimeo.test.login', token=access_token)
    user_id = userdata['user']['id']

    person = None
    if not request.user.is_anonymous():
        person = request.user.person
    account = account_for_vimeo_id(user_id, person=person)
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
    else:
        # If the account already existed (because some other user follows
        # that account and had imported objects by them, say), "merge" it
        # onto the signed-in user. (This does mean you can intentionally
        # move an account by signing in as a different django User and re-
        # associating that account, but that's appropriate.)
        account.person = person

    account.authinfo = ':'.join((access_token_data['oauth_token'], access_token_data['oauth_token_secret']))
    account.save()

    return HttpResponseRedirect(reverse('home'))


def signin_tumblr(request, form=None):
    csr = oauth.Consumer(*settings.TUMBLR_CONSUMER)
    client = oauth.Client(csr)
    oauth_callback = quote(request.build_absolute_uri(reverse('complete-tumblr')))

    http_url = 'http://www.tumblr.com/oauth/request_token'
    oauth_request = oauth.Request.from_consumer_and_token(csr, None,
        http_method='POST', http_url=http_url)
    oauth_request['oauth_callback'] = request.build_absolute_uri(reverse('complete-tumblr'))
    oauth_sign_method = oauth.SignatureMethod_HMAC_SHA1()
    oauth_request.sign_request(oauth_sign_method, csr, None)
    oauth_signing_base = oauth_sign_method.signing_base(oauth_request, csr, None)
    body = oauth_request.to_postdata()

    h = httplib2.Http()
    h.follow_redirects = 0
    normal_url = oauth_request.normalized_url
    log.debug('Making request to URL %r', normal_url)
    resp, content = h.request(normal_url, method=oauth_request.method, body=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})

    if resp.status != 200:
        raise ValueError('Unexpected response asking for Tumblr request token: %d %s' % (resp.status, resp.reason))
    if 'content-type' not in resp:
        raise ValueError("Response asking for Tumblr request token unexpectedly had no content type (is Tumblr down?)")

    request_token = dict(parse_qsl(content))
    request.session['tumblr_request_token'] = request_token

    return HttpResponseRedirect('http://www.tumblr.com/oauth/authorize?oauth_token=%s&oauth_access_type=write' % (request_token['oauth_token'],))


def complete_tumblr(request):
    try:
        request_token = request.session['tumblr_request_token']
    except KeyError:
        raise ValueError("Can't complete Tumblr authentication without a request token for this session")

    try:
        verifier = request.GET['oauth_verifier']
    except KeyError:
        # The viewer clicked "Deny", which is okay.
        return HttpResponseRedirect(reverse('home'))

    csr = oauth.Consumer(*settings.TUMBLR_CONSUMER)
    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])

    http_url = 'http://www.tumblr.com/oauth/access_token'
    oauth_request = oauth.Request.from_consumer_and_token(csr, token,
        http_method='POST', http_url=http_url)
    oauth_request['oauth_verifier'] = verifier
    oauth_sign_method = oauth.SignatureMethod_HMAC_SHA1()
    oauth_request.sign_request(oauth_sign_method, csr, token)
    oauth_signing_base = oauth_sign_method.signing_base(oauth_request, csr, token)
    body = oauth_request.to_postdata()

    h = httplib2.Http()
    h.follow_redirects = 0
    normal_url = oauth_request.normalized_url
    log.debug('Making request to URL %r', normal_url)
    resp, content = h.request(normal_url, method=oauth_request.method, body=body,
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if resp.status != 200:
        raise ValueError("Unexpected response exchanging for Tumblr access token: %d %s" % (resp.status, resp.reason))

    access_token_data = dict(parse_qsl(content))
    del request.session['tumblr_request_token']
    #request.session['access_token'] = access_token

    access_token = oauth.Token(access_token_data['oauth_token'], access_token_data['oauth_token_secret'])
    oauth_request = oauth.Request.from_consumer_and_token(csr, access_token,
        http_method='POST', http_url='http://www.tumblr.com/api/authenticate')
    oauth_request.sign_request(oauth_sign_method, csr, access_token)

    resp, cont = h.request(oauth_request.normalized_url, method=oauth_request.method,
        body=oauth_request.to_postdata(), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if resp.status != 200:
        raise ValueError("Unexpected response checking Tumblr access token: %d %s" % (resp.status, resp.reason))

    doc = ElementTree.fromstring(cont)
    blognodes = [blognode for blognode in doc.findall('./tumblelog') if blognode.attrib.get('is-primary') == 'yes']
    blognode = blognodes[0]

    person = None
    if not request.user.is_anonymous():
        person = request.user.person
    account = account_for_tumblelog_element(blognode, person=person)
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
    else:
        # If the account already existed (because some other user follows
        # that account and had imported objects by them, say), "merge" it
        # onto the signed-in user. (This does mean you can intentionally
        # move an account by signing in as a different django User and re-
        # associating that account, but that's appropriate.)
        account.person = person

    account.authinfo = ':'.join((access_token_data['oauth_token'], access_token_data['oauth_token_secret']))
    account.save()

    return HttpResponseRedirect(reverse('home'))


def signin_mlkshk(request):
    auth_params = {
        'response_type': 'code',
        'client_id': settings.MLKSHK_CONSUMER[0],
    }
    auth_url = urlunparse(('https', 'mlkshk.com', 'api/authorize', None, urlencode(auth_params), None))

    return HttpResponseRedirect(auth_url)


def complete_mlkshk(request):
    if 'error' in request.GET:
        raise ValueError("Received error code %r getting authorization code: %s" % (request.GET['error'], request.GET.get('error_description', '(no description)')))

    try:
        auth_code = request.GET['code']
    except KeyError:
        raise ValueError("Received no authorization code in response")

    token_params = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': request.build_absolute_uri(reverse('complete-mlkshk')),
        'client_id': settings.MLKSHK_CONSUMER[0],
        'client_secret': settings.MLKSHK_CONSUMER[1],
    }
    h = httplib2.Http()
    resp, cont = h.request('https://mlkshk.com/api/token', method='POST', body=urlencode(token_params), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if resp.status != 200:
        raise ValueError("Unexpected HTTP response requesting token: %d %s" % (resp.status, resp.reason))

    token_data = json.loads(cont)
    if 'access_token' not in token_data:
        raise ValueError("Mlkshk token response contains no access token")

    # Schweet. Try asking who this is.
    authtoken = token_data['access_token'].encode('utf8')
    authsecret = token_data['secret'].encode('utf8')
    userinfo = call_mlkshk('https://mlkshk.com/api/user', authtoken=authtoken, authsecret=authsecret)

    person = None
    if not request.user.is_anonymous():
        person = request.user.person
    account = account_for_mlkshk_userinfo(userinfo)
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
    else:
        # If the account already existed (because some other user follows
        # that account and had imported objects by them, say), "merge" it
        # onto the signed-in user. (This does mean you can intentionally
        # move an account by signing in as a different django User and re-
        # associating that account, but that's appropriate.)
        account.person = person

    account.authinfo = ':'.join((token_data['access_token'], token_data['secret']))
    account.save()

    return HttpResponseRedirect(reverse('home'))


def redirect_home(request):
    return HttpResponseRedirect(reverse('home'))


def json_stream(request):
    user = request.user
    if not user.is_authenticated():
        # FIXME: Also include an oauth2 auth challenge
        return HttpResponse("Auth is required", status=401, content_type='text/plain')

    try:
        person = user.person
    except Person.DoesNotExist:
        accounts = {}
    else:
        accounts = dict((acc.service, acc) for acc in person.accounts.all() if acc.authinfo)

    before, after = (datetime.strptime(request.GET[field], '%Y-%m-%dT%H:%M:%S') if field in request.GET else None for field in ('before', 'after'))
    limit = request.GET.get('limit', 20)
    stream_items = stream_items_for_user(user, before, after, limit=limit)

    def json_image_link(media):
        imagedata = {
            'url': media.image_url,
        }
        if media.width is not None:
            imagedata["width"] = media.width
        if media.height is not None:
            imagedata["height"] = media.height
        return imagedata

    def json_account(account):
        person = account.person
        accdata = {
            'display_name': person.display_name,
            'profile_url': person.permalink_url,
            'service': account.service,
            'ident': account.ident,
        }
        if person.avatar is not None:
            accdata["avatar"] = json_image_link(person.avatar)
        return accdata

    def json_object(obj):
        objdata = {
            'permalink_url': obj.permalink_url,
            'render_mode': obj.render_mode,
        }
        if obj.title is not None:
            objdata["title"] = obj.title
        if obj.body:
            objdata["body_html"] = obj.body # FIXME: How can we make this always be HTML even when the underlying storage isn't?
        if obj.image is not None:
            objdata["image"] = json_image_link(obj.image)
        if obj.author is not None:
            objdata["author"] = json_account(obj.author)
        return objdata

    if request.GET.get('html'):
        rc = RequestContext(request)
        result = {'items': [{
            'id': item.id,
            'time': item.time.isoformat(),
            'html': render_to_string('leapfrog/streamitem.jj', {
                'item': item,
                'accounts': accounts,
            }, context_instance=rc),
        } for item in stream_items]}
    else:
        result = {'items': [{
            'id': item.id,
            'time': item.time.isoformat(),
            'verb': item.why_verb,
            'actor': json_account(item.why_account),
            'object': json_object(item.obj),
        } for item in stream_items]}

    return HttpResponse(json.dumps(result), mimetype="application/json")


def respond_twitter(request, urlpattern):
    if request.method != 'POST':
        resp = HttpResponse('POST is required', status=405, content_type='text/plain')
        resp['Allow'] = ('POST',)
        return resp

    user = request.user
    if not user.is_authenticated():
        return HttpResponse('Authentication required to respond', status=400, content_type='text/plain')
    try:
        person = user.person
    except Person.DoesNotExist:
        return HttpResponse('Real reader account required to respond', status=400, content_type='text/plain')

    try:
        tweet_id = request.POST['tweet']
    except KeyError:
        tweet_id = False
    if not tweet_id:
        return HttpResponse("Parameter 'tweet' is required", status=400, content_type='text/plain')

    # TODO: get only one account once we enforce (service,person) uniqueness
    accounts = person.accounts.filter(service='twitter.com')
    for account in accounts:
        # FAVED
        csr = oauth.Consumer(*settings.TWITTER_CONSUMER)
        twitter_token = account.authinfo.split(':', 1)
        log.debug('Authorizing client as Twitter user %s with token %s : %s', account.display_name, *twitter_token)
        token = oauth.Token(*twitter_token)
        client = oauth.Client(csr, token)

        resp, content = client.request(urlpattern % {'tweet_id': tweet_id}, method='POST')

        if resp.status != 200:
            try:
                errordata = json.loads(content)
            except ValueError:
                error = content
            else:
                error = errordata.get('error', content)

            if error == 'You have already favorited this status.':
                # Yay, just go on.
                continue

            log.warning('Unexpected HTTP response %d %s trying to respond to tweet %s for %s (%s): %s',
                resp.status, resp.reason, tweet_id, account.ident, account.display_name, error)

            if error == 'Read-only application cannot POST':
                ret_error = 'Our Twitter token for that account is read-only'
            else:
                ret_error = 'Error favoriting tweet: %s' % error
            return HttpResponse(ret_error, status=400, content_type='text/plain')

    return HttpResponse('OK', content_type='text/plain')


def favorite_twitter(request):
    return respond_twitter(request, 'http://api.twitter.com/1/favorites/create/%(tweet_id)s.json')


def retweet_twitter(request):
    return respond_twitter(request, 'http://api.twitter.com/1/statuses/retweet/%(tweet_id)s.json')


def favorite_typepad(request):
    if request.method != 'POST':
        resp = HttpResponse('POST is required', status=405, content_type='text/plain')
        resp['Allow'] = ('POST',)
        return resp

    user = request.user
    if not user.is_authenticated():
        return HttpResponse('Authentication required to respond', status=400, content_type='text/plain')
    try:
        person = user.person
    except Person.DoesNotExist:
        return HttpResponse('Real reader account required to respond', status=400, content_type='text/plain')

    try:
        post_id = request.POST['post']
    except KeyError:
        post_id = False
    if not post_id:
        return HttpResponse("Parameter 'post' is required", status=400, content_type='text/plain')

    # TODO: get only one account once we enforce (service,person) uniqueness
    accounts = person.accounts.filter(service='typepad.com')
    for account in accounts:
        # FAVED
        csr = oauth.Consumer(*settings.TYPEPAD_CONSUMER)
        typepad_token = account.authinfo.split(':', 1)
        log.debug('Authorizing client as TypePad user %s with token %s : %s', account.display_name, typepad_token[0], typepad_token[1])
        token = oauth.Token(*typepad_token)
        # This is a POST, so the stock oauth2 Client works.
        client = oauth.Client(csr, token)

        t = typd.TypePad(endpoint='https://api.typepad.com/', client=client)
        log.debug('Trying to add post ID %r to favorites of user ID %r', post_id, account.ident)
        try:
            try:
                t.users.post_to_favorites(account.ident, typd.Favorite(
                    author=typd.User(id='tag:api.typepad.com,2009:%s' % account.ident, url_id=account.ident),
                    in_reply_to=typd.AssetRef(id='tag:api.typepad.com,2009:%s' % post_id, url_id=post_id),
                ))
            except typd.Forbidden:
                # See if it's a group asset.
                unauth_t = typd.TypePad(endpoint='http://api.typepad.com/')
                asset = unauth_t.assets.get(post_id)
                if asset.container.object_type == 'Group':
                    return HttpResponse("Can't favorite Group assets", status=400, content_type='text/plain')
                raise
        except typd.HttpError, exc:
            log.warning('Unexpected HTTP error %s trying to favorite %s for TypePad user %s: %s' % (type(exc).__name__, post_id, account.display_name, str(exc)))
            return HttpResponse('Error favoriting post: %s' % str(exc), status=400, content_type='text/plain')

    return HttpResponse('OK', content_type='text/plain')


def favorite_flickr(request):
    if request.method != 'POST':
        resp = HttpResponse('POST is required', status=405, content_type='text/plain')
        resp['Allow'] = ('POST',)
        return resp

    user = request.user
    if not user.is_authenticated():
        return HttpResponse('Authentication required to respond', status=400, content_type='text/plain')
    try:
        person = user.person
    except Person.DoesNotExist:
        return HttpResponse('Real reader account required to respond', status=400, content_type='text/plain')

    try:
        photo_id = request.POST['photo']
    except KeyError:
        photo_id = False
    if not photo_id:
        return HttpResponse("Parameter 'photo' is required", status=400, content_type='text/plain')

    # TODO: get only one account once we enforce (service,person) uniqueness
    accounts = person.accounts.filter(service='flickr.com')
    for account in accounts:
        try:
            call_flickr('flickr.favorites.add', sign=True, auth_token=account.authinfo, photo_id=photo_id)
        except Exception, exc:
            log.warning("Error favoriting photo %s for Flickr user %s: %s", photo_id, account.display_name, str(exc))
            return HttpResponse('Error favoriting photo: %s' % str(exc), status=400, content_type='text/plain')

    return HttpResponse('OK', content_type='text/plain')


def like_tumblr(request):
    if request.method != 'POST':
        resp = HttpResponse('POST is required', status=405, content_type='text/plain')
        resp['Allow'] = ('POST',)
        return resp

    user = request.user
    if not user.is_authenticated():
        return HttpResponse('Authentication required to respond', status=400, content_type='text/plain')
    try:
        person = user.person
    except Person.DoesNotExist:
        return HttpResponse('Real reader account required to respond', status=400, content_type='text/plain')

    try:
        account = person.accounts.get(service='tumblr.com')
    except Account.DoesNotExist:
        return HttpResponse('Tumblr account is required to respond on Tumblr', status=400, content_type='text/plain')
    if not account.authinfo:
        return HttpResponse('Tumblr account we can use with the API is required to respond on Tumblr', status=400, content_type='text/plain')

    try:
        post_id = request.POST['post']
    except KeyError:
        post_id = False
    if not post_id:
        return HttpResponse("Parameter 'post' is required", status=400, content_type='text/plain')

    # Ugggh now get the original object because Tumblr makes us use the API
    # on the object's own Tumblr domain to get the reblog key.
    try:
        obj = Object.objects.get(service='tumblr.com', foreign_id=post_id)
    except Object.DoesNotExist:
        return HttpResponse('No local record of Tumblr post #%d' % post_id, status=400, content_type='text/plain')

    obj_urlparts = urlparse(obj.permalink_url)
    api_url = urlunparse(('http', obj_urlparts.netloc, '/api/read', None, urlencode({'id': post_id}), None))

    h = httplib2.Http()
    resp, cont = h.request(api_url)
    if resp.status != 200:
        return HttpResponse("Unexpected HTTP response finding reblog key for Tumblr post #%s: %d %s"
            % (post_id, resp.status, resp.reason), status=400, content_type='text/plain')

    doc = ElementTree.fromstring(cont)
    post_el = doc.find('./posts/post')
    reblog_key = post_el.attrib['reblog-key']

    csr = oauth.Consumer(*settings.TUMBLR_CONSUMER)
    token = oauth.Token(*account.authinfo.split(':', 1))
    client = oauth.Client(csr, token)

    body = urlencode({'post-id': post_id, 'reblog-key': reblog_key})
    resp, cont = client.request('http://www.tumblr.com/api/like', method='POST', body=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if resp.status != 200:
        return HttpResponse("Unexpected HTTP response 'liking' Tumblr post #%s: %d %s"
            % (post_id, resp.status, resp.reason), status=400, content_type='text/plain')

    return HttpResponse('OK', content_type='text/plain')


@login_required
def new_items(request):
    maxstreamitem = int(request.GET.get('maxstreamitem', 0))
    maxreplyitem = int(request.GET.get('maxreplyitem', 0))

    streamitems = request.user.stream_items.filter(id__gt=maxstreamitem).count()
    replies = request.user.reply_stream_items.filter(id__gt=maxreplyitem).count()

    return HttpResponse(json.dumps({
        'streamitems': streamitems,
        'replyitems': replies,
    }), content_type='application/json')


def detach_account(request):
    if request.method != 'POST':
        resp = HttpResponse('POST is required', status=405, content_type='text/plain')
        resp['Allow'] = ('POST',)
        return resp

    user = request.user
    if not user.is_authenticated():
        return HttpResponse('Authentication required to respond', status=400, content_type='text/plain')
    try:
        person = user.person
    except Person.DoesNotExist:
        return HttpResponse('Real reader account required to respond', status=400, content_type='text/plain')

    # Which account is that?
    try:
        account_pk = request.POST['account']
    except KeyError:
        return HttpResponse("Parameter 'account' is required", status=400, content_type='text/plain')
    try:
        account = Account.objects.get(pk=account_pk)
    except Account.DoesNotExist:
        return HttpResponse("Parameter 'account' must be a valid account ID", status=400, content_type='text/plain')
    if account.person.pk != person.pk:
        return HttpResponse("Parameter 'account' must be a valid account ID", status=400, content_type='text/plain')

    # Put this account on a different person. (It probably has data attached, so we don't delete it.)
    new_person = Person(
        display_name=account.display_name,
    )
    new_person.save()
    account.person = new_person
    account.authinfo = ''
    account.save()

    return HttpResponse('OK', content_type='text/plain')


@login_required
def save_setting(request):
    if request.method != 'POST':
        resp = HttpResponse('POST is required', status=405, content_type='text/plain')
        resp['Allow'] = 'POST'
        return resp

    key, value = request.POST['key'], request.POST['value']

    setting, created = UserSetting.objects.get_or_create(user=request.user, key=key,
        defaults={'value': value})
    if not created:
        setting.value = value
        setting.save()

    return HttpResponse('OK', content_type='text/plain')
