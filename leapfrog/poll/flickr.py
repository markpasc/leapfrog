from __future__ import division

from datetime import datetime
from hashlib import md5
import json
import logging
import re
from urllib import urlencode
from urlparse import urlunparse

from django.conf import settings
import httplib2

from leapfrog.models import Account, Media, Person, Object, UserStream


log = logging.getLogger(__name__)


def account_for_flickr_id(nsid, person=None):
    try:
        # TODO: update flickr avatar pictures (but that requires fetching their people info speculatively)
        return Account.objects.get(service='flickr.com', ident=nsid)
    except Account.DoesNotExist:
        pass

    result = call_flickr('flickr.people.getInfo', user_id=nsid)
    persondata = result['person']

    if person is None:
        if int(persondata['iconfarm']) == 0:
            avatar = None
        else:
            avatar = Media(
                image_url='http://farm%s.static.flickr.com/%s/buddyicons/%s.jpg'
                    % (persondata['iconfarm'], persondata['iconserver'], nsid),
                width=48,
                height=48,
            )
            avatar.save()

        namenode = persondata.get('realname', persondata.get('username'))

        person = Person(
            display_name=namenode['_content'],
            permalink_url=persondata['profileurl']['_content'],
            avatar=avatar,
        )
        person.save()

    try:
        display_name = persondata['realname']['_content']
    except KeyError:
        display_name = None

    acc = Account(
        service='flickr.com',
        ident=nsid,
        display_name=display_name or nsid,
        person=person,
    )
    acc.save()
    return acc


def sign_flickr_query(query):
    sign_base = ''.join('%s%s' % (k, v) for k, v in sorted(query.items(), key=lambda i: i[0]))

    signer = md5()
    signer.update(settings.FLICKR_KEY[1])
    signer.update(sign_base)

    query['api_sig'] = signer.hexdigest()


def call_flickr(method, sign=False, **kwargs):
    query = dict(kwargs)
    query['api_key'] = settings.FLICKR_KEY[0]
    query['method'] = method
    query['format'] = 'json'
    query['nojsoncallback'] = 1

    if sign:
        sign_flickr_query(query)

    url = urlunparse(('http', 'api.flickr.com', 'services/rest/', None, urlencode(query), None))

    h = httplib2.Http()
    resp, cont = h.request(url)
    if resp.status != 200:
        raise ValueError("Unexpected response querying Flickr method %s: %d %s" % (method, resp.status, resp.reason))

    result = json.loads(cont)
    if result.get('stat') != 'ok':
        raise ValueError("Error making Flickr request with method %s: %s" % (method, result.get('message')))

    return result


def photo_url_for_photo(photodata):
    return 'http://farm%(farm)s.static.flickr.com/%(server)s/%(id)s_%(secret)s_b.jpg' % photodata


def make_object_from_photo_data(photodata):
    log.debug("Creating new object for %s's Flickr photo #%s", photodata['owner'], photodata['id'])

    # We aren't supposed to be able to ask for the dimensions, but we can, so use 'em.
    try:
        height, width = [int(photodata[key]) for key in ('o_height', 'o_width')]
    except KeyError:
        # Didn't get those, so we need to get the biggest size we can see.
        photosizes = call_flickr('flickr.photos.getSizes', photo_id=photodata['id'])
        largest = max(photosizes['sizes']['size'], key=lambda x: int(x['width']) * int(x['height']))
        height, width = [int(largest[key]) for key in ('height', 'width')]
        photourl = largest['source']
    else:
        photourl = photo_url_for_photo(photodata)

    if height > width:
        width = int(1024 * width / height)
        height = 1024
    else:
        height = int(1024 * height / width)
        width = 1024

    image = Media(
        image_url=photourl,
        width=width,
        height=height,
    )
    image.save()

    try:
        owner_nsid = photodata['owner']['nsid']
    except TypeError:
        owner_nsid = photodata['owner']
    try:
        phototitle = photodata['title']['_content']
    except TypeError:
        phototitle = photodata['title']

    timestr = photodata.get('dateupload', photodata.get('dateuploaded'))
    if timestr is None:
        raise ValueError("Couldn't find an upload date (neither dateupload nor dateuploaded) in photodata %r" % photodata)

    obj = Object(
        service='flickr.com',
        foreign_id=photodata['id'],
        render_mode='image',
        title=phototitle,
        #body=,
        public=True if photodata.get('ispublic') else False,
        image=image,
        time=datetime.utcfromtimestamp(int(timestr)),
        permalink_url='http://www.flickr.com/photos/%s/%s/' % (owner_nsid, photodata['id']),
        author=account_for_flickr_id(owner_nsid),
    )
    obj.save()

    return obj


def object_from_url(url):
    mo = re.match(r'http:// [^/]* flickr\.com/ photos/ [^/]+/ (\d+)', url, re.MULTILINE | re.DOTALL | re.VERBOSE)
    photo_id = mo.group(1)

    resp = call_flickr('flickr.photos.getInfo', photo_id=photo_id, extras='date_upload,o_dims')
    photodata = resp['photo']

    try:
        obj = Object.objects.get(service='flickr.com', foreign_id=photodata['id'])
    except Object.DoesNotExist:
        pass
    else:
        log.debug("Reusing existing object %r for Flickr photo #%s", obj, photodata['id'])
        return obj

    obj = make_object_from_photo_data(photodata)
    return obj


def poll_flickr(account):
    user = account.person.user
    if user is None:
        return

    recent = call_flickr('flickr.photos.getContactsPhotos', sign=True, auth_token=account.authinfo)
    for slim_photodata in recent['photos']['photo']:
        photo_id = slim_photodata['id']
        try:
            obj = Object.objects.get(service='flickr.com', foreign_id=photo_id)
            log.debug("Reusing existing object %r for Flickr photo #%s", obj, photo_id)
        except Object.DoesNotExist:
            resp = call_flickr('flickr.photos.getInfo', photo_id=photo_id, extras='date_upload,o_dims',
                sign=True, auth_token=account.authinfo)
            photodata = resp['photo']

            # Omit instagram and picplz shares.
            for tagdata in photodata['tags']['tag']:
                if tagdata['raw'] in ('uploaded:by=instagram', 'picplz'):
                    continue

            try:
                obj = make_object_from_photo_data(photodata)
            except Exception, exc:
                log.exception(exc)
                continue
            if obj is None:
                continue

        UserStream.objects.get_or_create(user=user, obj=obj,
            defaults={'time': obj.time, 'why_account': obj.author, 'why_verb': 'post'})
