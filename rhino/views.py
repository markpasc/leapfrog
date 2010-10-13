import json
from urllib import urlencode, quote
from urlparse import parse_qsl

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
import oauth2 as oauth

from rhino.poll.twitter import account_for_twitter_user


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

    replies = user.reply_stream_items.filter(root_time__range=(stream_items[-1].time, stream_items[0].time)).select_related()
    reply_by_item = dict()
    for reply in replies:
        item_replies = reply_by_item.setdefault(reply.root_id, set())
        item_replies.add(reply)
    for item in stream_items:
        reply_set = reply_by_item.get(item.obj_id, set())
        item.replies = sorted(iter(reply_set), key=lambda i: i.reply_time)

    data = {
        'stream_items': stream_items,
        'replies': replies,
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
    request.session['request_token'] = request_token

    return HttpResponseRedirect('https://api.twitter.com/oauth/authenticate?oauth_token=%s' % request_token['oauth_token'])


def complete_twitter(request):
    try:
        request_token = request.session['request_token']
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
    del request.session['request_token']
    #request.session['access_token'] = access_token

    # But who is that?
    client = oauth.Client(csr, oauth.Token(access_token['oauth_token'], access_token['oauth_token_secret']))
    resp, content = client.request('https://api.twitter.com/1/account/verify_credentials.json')
    if resp.status != 200:
        raise ValueError("Unexpected response verifying credentials: %d %s" % (resp.status, resp.reason))

    userdata = json.loads(content)

    person = None
    if not request.user.is_anonymous:
        person = request.user.person
    account = account_for_twitter_user(userdata, person=person)
    if request.user.is_anonymous:
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
