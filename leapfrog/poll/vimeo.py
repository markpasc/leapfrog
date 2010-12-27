from __future__ import division

from datetime import datetime
import json
import logging
import re
from urllib import urlencode

from django.conf import settings
import httplib2
import oauth2 as oauth

from leapfrog.models import Account, Media, Person, Object, UserStream


log = logging.getLogger(__name__)


def call_vimeo(method, token=None, **kwargs):
    csr = oauth.Consumer(*settings.VIMEO_CONSUMER)

    http_url = 'http://vimeo.com/api/rest/v2?format=json&method=%s' % method
    if kwargs:
        http_url = '&'.join((http_url, urlencode(kwargs)))
    oauth_request = oauth.Request.from_consumer_and_token(csr, token,
        http_method='GET', http_url=http_url)
    oauth_sign_method = oauth.SignatureMethod_HMAC_SHA1()
    oauth_request.sign_request(oauth_sign_method, csr, token)
    oauth_signing_base = oauth_sign_method.signing_base(oauth_request, csr, token)
    oauth_header = oauth_request.to_header()
    h = httplib2.Http()
    h.follow_redirects = 0
    normal_url = oauth_request.to_url()
    log.debug('Making request to URL %r', normal_url)
    resp, content = h.request(normal_url, method=oauth_request.method,
        headers=oauth_header)
    if resp.status != 200:
        raise ValueError("Unexpected response verifying Vimeo credentials: %d %s" % (resp.status, resp.reason))

    data = json.loads(content)
    if data['stat'] == 'fail':
        err = data['err']
        raise ValueError("Error retrieving data for %s call: %s: %s" % (method, err['msg'], err['expl']))

    return data


def account_for_vimeo_id(user_id, person=None):
    try:
        return Account.objects.get(service='vimeo.com', ident=user_id)
    except Account.DoesNotExist:
        pass

    # get vimeo data
    log.debug('Getting info on user %r', user_id)
    userdata = call_vimeo('vimeo.people.getInfo', user_id=user_id)
    persondata = userdata['person']

    if person is None:
        portraits = persondata.get('portraits', {}).get('portrait')
        avatar = None
        if portraits is not None:
            portraits = sorted([portrait for portrait in portraits if int(portrait['height']) >= 75], key=lambda x: int(x['height']))
            if portraits:
                portrait = portraits[0]
                avatar = Media(
                    image_url=portrait['_content'],
                    width=int(portrait['width']),
                    height=int(portrait['height']),
                )
                avatar.save()

        person = Person(
            display_name=persondata['display_name'],
            permalink_url=persondata['profileurl'],
            avatar=avatar,
        )
        person.save()

    acc = Account(
        service='vimeo.com',
        ident=user_id,
        display_name=persondata.get('display_name', persondata.get('username', user_id)),
        person=person,
    )
    acc.save()

    return acc


def object_from_video_data(videodata):
    video_id = videodata['id']
    try:
        return Object.objects.get(service='vimeo.com', foreign_id=video_id)
    except Object.DoesNotExist:
        pass

    author = account_for_vimeo_id(videodata['owner']['id'])
    permalink_url = [urldata['_content'] for urldata in videodata['urls']['url'] if urldata['type'] == 'video'][0]

    width, height = [int(videodata[key]) for key in ('width', 'height')]
    if width > 660:
        height = 660 * height / width
        width = 660
    body = ("""<iframe src="http://player.vimeo.com/video/%s" width="%d" height="%d"></iframe>"""
        % (video_id, width, height))

    obj = Object(
        service='vimeo.com',
        foreign_id=video_id,
        render_mode='mixed',
        title=videodata['title'],
        body=body,
        time=datetime.strptime(videodata['upload_date'], '%Y-%m-%d %H:%M:%S'),
        permalink_url=permalink_url,
        author=author,
    )
    obj.save()

    return obj


def object_from_url(url):
    mo = re.match(r'http://vimeo\.com/ (\d+)', url, re.MULTILINE | re.DOTALL | re.VERBOSE)
    if mo is None:
        return
    video_id = mo.group(1)

    videoresp = call_vimeo('vimeo.videos.getInfo', video_id=video_id)
    videodata = videoresp['video'][0]
    return object_from_video_data(videodata)


def poll_vimeo(account):
    user = account.person.user
    if user is None:
        return

    token = oauth.Token(*account.authinfo.split(':'))
    subdata = call_vimeo('vimeo.videos.getSubscriptions', token=token, full_response='true')
    for videodata in subdata['videos']['video']:
        try:
            obj = object_from_video_data(videodata)
            # TODO: save videos from "like" subscriptions as shares
            UserStream.objects.get_or_create(user=user, obj=obj,
                defaults={'time': obj.time, 'why_account': obj.author, 'why_verb': 'post'})
        except Exception, exc:
            log.exception(exc)
