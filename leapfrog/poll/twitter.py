from datetime import datetime
import json
import re

import httplib2

from leapfrog.models import Object, Account, Person, Media


def account_for_twitter_user(userdata, person=None):
    try:
        account = Account.objects.get(service='twitter.com', ident=str(userdata['id']))
    except Account.DoesNotExist:
        if person is None:
            avatar = Media(
                width=48,
                height=48,
                image_url=userdata['profile_image_url'],
            )
            avatar.save()
            person = Person(
                display_name=userdata['name'],
                avatar=avatar,
                permalink_url='http://twitter.com/%s' % userdata['screen_name'],
            )
            person.save()
        account = Account(
            service='twitter.com',
            ident=str(userdata['id']),
            display_name=userdata['name'],
            person=person,
            status_background_color=userdata.get('profile_background_color') or '',
            status_background_image_url=userdata.get('profile_background_image_url') or '',
            status_background_tile=userdata.get('profile_background_tile') or False,
        )
        account.save()
    else:
        person = account.person
        if not person.avatar_source or person.avatar_source == 'twitter.com':
            if not person.avatar or person.avatar.image_url != userdata['profile_image_url']:
                avatar = Media(
                    width=48,
                    height=48,
                    image_url=userdata['profile_image_url'],
                )
                avatar.save()
                person.avatar = avatar
                person.avatar_source = 'twitter.com'
                person.save()
            elif not person.avatar_source:
                person.avatar_source = 'twitter.com'
                person.save()

        # We can always update these (but only pay for saving if they changed).
        if not (account.status_background_color == (userdata.get('profile_background_color') or '')
            and account.status_background_image_url == userdata.get('profile_background_image_url') or ''
            and account.status_background_tile == (userdata.get('profile_background_tile') or False)):
            account.status_background_color = userdata.get('profile_background_color') or ''
            account.status_background_image_url = userdata.get('profile_background_image_url') or ''
            account.status_background_tile = userdata.get('profile_background_tile') or False
            account.save()

    return account


def object_from_twitpic_url(url):
    mo = re.match(r'http://twitpic\.com/(\w+)', url)
    twitpic_id = mo.group(1)

    try:
        return Object.objects.get(service='twitpic.com', foreign_id=twitpic_id)
    except Object.DoesNotExist:
        pass

    h = httplib2.Http()
    resp, content = h.request('http://api.twitpic.com/2/media/show.json?id=%s' % twitpic_id)

    try:
        picdata = json.loads(content)
    except ValueError:
        # Couldn't get twitpic infos... probably because we're banned.
        return None
    if picdata.get('errors'):
        # Hmm, well, guess that didn't work.
        return None

    userdata = picdata['user']
    # ugh, why did they rename these
    userdata['id'] = userdata['twitter_id']
    userdata['screen_name'] = userdata['username']
    userdata['profile_image_url'] = userdata['avatar_url']

    pic = Media(
        image_url='http://twitpic.com/show/large/%s' % twitpic_id,
        width=int(picdata['width']),
        height=int(picdata['height']),
    )
    pic.save()
    obj = Object(
        service='twitpic.com',
        foreign_id=twitpic_id,
        render_mode='image',
        title=picdata['message'],
        image=pic,
        author=account_for_twitter_user(userdata),
        time=datetime.strptime(picdata['timestamp'], '%Y-%m-%d %H:%M:%S'),
        permalink_url=url,
    )
    obj.save()
    return obj
