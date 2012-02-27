from datetime import datetime, timedelta
import json
import logging
import re

from django.conf import settings
from django.utils.http import urlquote
import httplib2
import oauth2 as oauth

from leapfrog.models import Object, Account, Person, UserStream, Media, UserReplyStream
import leapfrog.poll.embedlam


log = logging.getLogger(__name__)


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


def tweet_html(tweetdata):
    tweet = tweetdata['text']
    entities = tweetdata.get('entities', {})

    mutations = list()
    for urldata in entities.get('urls', ()):
        orig_url = urldata['url']
        url = urldata['expanded_url'] or urldata['url']

        # Make sure the URL is ascii-safe so we can enstringify it.
        url = urlquote(url, safe='/&=:;#?+*')

        start, end = urldata['indices']
        text = urldata.get('text', tweet[start:end])
        classattr = 'class="%s" ' % urldata['class'] if 'class' in urldata else ''
        mutations.append({
            'indices': (start, end),
            'html': u"""<a %shref="%s" title="%s">%s</a>""" % (classattr, orig_url, url, text),
        })
    for mediadata in entities.get('media', ()):
        size = mediadata['sizes']['large']
        mutations.append({
            'indices': mediadata['indices'],
            'html': u"""<a href="%s"><img src="%s" width="%s" height="%s" alt=""></a>"""
                % (mediadata['expanded_url'], mediadata['media_url'], size['w'], size['h']),
        })
    for mentiondata in entities.get('user_mentions', ()):
        mutations.append({
            'indices': mentiondata['indices'],
            'html': u"""@<a href="http://twitter.com/%(screen_name)s" title="%(name)s">%(screen_name)s</a>""" % mentiondata,
        })
    for tagdata in entities.get('hashtags', ()):
        mutations.append({
            'indices': tagdata['indices'],
            'html': u"""<a href="http://twitter.com/search?q=%%23%(text)s">#%(text)s</a>""" % tagdata,
        })

    # Mutate bare '&'s into escaped entities too.
    for mo in re.finditer(r'&(?!gt;|lt;)', tweet):
        mutations.append({
            'indices': mo.span(),
            'html': '&amp;',
        })
    # Let's also display line feeds.
    for mo in re.finditer(r'\n', tweet):
        mutations.append({
            'indices': mo.span(),
            'html': '<br>',
        })

    # Mutate the tweet from the end, so the replacements don't invalidate the remaining indices.
    for mutation in sorted(mutations, key=lambda x: x['indices'][0], reverse=True):
        indices = mutation['indices']
        tweet = tweet[:indices[0]] + mutation['html'] + tweet[indices[1]:]

    return tweet


url_re = re.compile(r"""
    (?: (?<= \A )
      | (?<= [\s.:;?\-\]<\(] ) )

    https?://
    [-\w;/?:@&=+$.!~*'()%,#]+
    [\w/]

    (?= \Z | [\s\.,!:;?\-\[\]>\)] )
""", re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)

mention_re = re.compile(r"""
    (?: (?<= \A ) | (?<= \s ) )
    @ (\w+)
""", re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)

tag_re = re.compile(r"""
    (?: (?<= \A ) | (?<= \s ) )  # BOT or whitespace
    \# (\w\S*\w)      # tag
    (?<! 's )         # but don't end with 's
""", re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE)

def synthesize_entities(tweetdata):
    if 'entities' in tweetdata:
        return

    tweettext = tweetdata['text']
    ents = {
        'urls': [],
        'hashtags': [],
        'user_mentions': [],
    }

    for match in url_re.finditer(tweettext):
        ents['urls'].append({
            'expanded_url': None,
            'url': match.group(0),
            'indices': [match.start(), match.end()],
        })

    for match in mention_re.finditer(tweettext):
        ents['user_mentions'].append({
            'id': None,  # we would have to get this if we ever used it
            'name': match.group(1),  # TODO: get this from the API? ugh
            'screen_name': match.group(1),
            'indices': [match.start(), match.end()],
        })

    for match in tag_re.finditer(tweettext):
        ents['hashtags'].append({
            'text': match.group(1),
            'indices': [match.start(), match.end()],
        })

    tweetdata['entities'] = ents


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


def object_from_tweet_id(tweet_id, client=None):
    try:
        return False, Object.objects.get(service='twitter.com', foreign_id=str(tweet_id))
    except Object.DoesNotExist:
        pass

    if client is None:
        # Be unauth'd then.
        client = httplib2.Http()

    resp, content = client.request('http://api.twitter.com/1/statuses/show/%d.json?include_entities=1'
        % tweet_id)
    if resp.status in (403, 404, 500, 502, 503):
        # Hmm, no such tweet, somebody's private tweet, or we just can't get it right now, I guess.
        return False, None
    if resp.status != 200:
        raise ValueError("Unexpected %d %s response fetching tweet #%s"
            % (resp.status, resp.reason, tweet_id))

    tweetdata = json.loads(content)
    if 'entities' not in tweetdata:
        synthesize_entities(tweetdata)
    log.debug("    Let's make a new tweet for %s status #%d", tweetdata['user']['screen_name'], tweetdata['id'])
    # If it's really a share, this tweet is transitively in reply to the shared thing, so this is fine.
    return raw_object_for_tweet(tweetdata, client)


def object_from_url(url):
    mo = re.match(r'http://twitter\.com/ (?: \#!/ )? [^/]+/ status/ (\d+)', url, re.MULTILINE | re.DOTALL | re.VERBOSE)
    if mo is None:
        return
    tweet_id = mo.group(1)
    really_a_share, tweet_obj = object_from_tweet_id(int(tweet_id))
    return tweet_obj


def raw_object_for_tweet(tweetdata, client):
    """Returns the normalized Object for the given tweetdata, and whether
    that Object represents that tweet or the thing the tweet is sharing.

    This is returned as a tuple containing (a) whether the tweet is a
    share, and (b) the ``leapfrog.models.Object`` reference for that tweet
    data, in that order.

    """
    try:
        return False, Object.objects.get(service='twitter.com', foreign_id=str(tweetdata['id']))
    except Object.DoesNotExist:
        pass

    log.debug('Making new tweet for %s status #%d', tweetdata['user']['screen_name'], tweetdata['id'])

    source = tweetdata.get('source', '')
    for meh_source in ('foursquare.com', 'soundtracking.com', 'goscoville.com', 'paper.li'):
        if meh_source in source:
            log.debug("Skipping %s's tweet #%d as it's from %s", tweetdata['user']['screen_name'], tweetdata['id'], meh_source)
            return False, None

    in_reply_to = None
    if tweetdata.get('in_reply_to_status_id'):
        # Uh oh, gotta get that tweet.
        # TODO: remove the mention from the front of the tweet
        next_tweetid = tweetdata['in_reply_to_status_id']
        really_a_share, in_reply_to = object_from_tweet_id(next_tweetid, client)
        if in_reply_to is not None and not in_reply_to.public:
            # No.
            in_reply_to = None

    # Is this status a reply to a link?
    elif len(tweetdata['entities']['urls']) == 1 and not tweetdata['entities'].get('media', ()):
        about_urldata = tweetdata['entities']['urls'][0]
        about_url = about_urldata['expanded_url'] or about_urldata['url']

        about_page = None
        try:
            about_page = leapfrog.poll.embedlam.Page(about_url)
        except leapfrog.poll.embedlam.RequestError, exc:
            log.debug("Expected problem making page data from reference %s of %s's tweet %s", about_url, tweetdata['user']['screen_name'], tweetdata['id'], exc_info=True)
        except ValueError, exc:
            log.error("Error making page data from referent %s of %s's tweet %s", about_url, tweetdata['user']['screen_name'], tweetdata['id'])
            log.exception(exc)

        if about_page is not None:
            try:
                in_reply_to = about_page.to_object()
            except leapfrog.poll.embedlam.RequestError, exc:
                log.debug("Expected problem making object from referent %s of %s's tweet %s", about_url, tweetdata['user']['screen_name'], tweetdata['id'], exc_info=True)
            except ValueError, exc:
                log.error("Error making object from referent %s of %s's tweet %s", about_url, tweetdata['user']['screen_name'], tweetdata['id'])
                log.exception(exc)

            # If the tweet was only the object's url and its title, make it a share.
            if in_reply_to is not None:
                tweettext = tweetdata['text']
                link_starts, link_ends = about_urldata['indices']
                tweettext = tweettext[:link_starts] + tweettext[link_ends:]
                tweettext = tweettext.lower()
                tweettext = re.sub(r'\s', '', tweettext)
                if in_reply_to.title:
                    log.debug("Tweet #%s in reply to %r has text %r before removing title %r", str(tweetdata['id']), in_reply_to, tweettext, in_reply_to.title)
                    title = in_reply_to.title.lower()
                    title = re.sub(r'\s', '', title)
                    tweettext = tweettext.replace(title, '')
                log.debug("Tweet #%s in reply to %r has remaining text %r", str(tweetdata['id']), in_reply_to, tweettext)

                if not tweettext:
                    return True, in_reply_to

                # Otherwise, pull all the below data from the target object.
                about_page = in_reply_to

            # Use the real canonical URL.
            about_urldata['expanded_url'] = about_page.permalink_url

            # Otherwise, suggest the title as link text.
            if about_page.title:
                # Don't replace the if the link text is not identical to the
                # URL (if it's an autolinked domain name, we'd break how the
                # tweet reads).
                tweet_text = tweetdata['text']
                start, end = about_urldata['indices']
                if tweet_text[start:end] == about_urldata['url']:
                    # Mark links we change the text of as aboutlinks.
                    about_urldata['text'] = about_page.title
                    about_urldata['class'] = 'aboutlink'

    # Update the status's links anyway.
    else:
        try:
            urls = tweetdata['entities']['urls']
        except KeyError:
            urls = ()
        for urldata in urls:
            url = urldata.get('expanded_url') or urldata.get('url')
            if not url:
                continue
            try:
                url_page = leapfrog.poll.embedlam.Page(url)
            except ValueError:
                # meh
                continue

            urldata['expanded_url'] = url_page.permalink_url

            if url_page.title:
                # Don't replace the if the link text is not identical to the
                # URL (if it's an autolinked domain name, we'd break how the
                # tweet reads).
                tweet_text = tweetdata['text']
                start, end = urldata['indices']
                if tweet_text[start:end] == urldata['url']:
                    # Mark links we change the text of as aboutlinks.
                    urldata['text'] = url_page.title
                    urldata['class'] = 'aboutlink'

    tweet = Object(
        service='twitter.com',
        foreign_id=str(tweetdata['id']),
        render_mode='status',
        body=tweet_html(tweetdata),
        time=datetime.strptime(tweetdata['created_at'], '%a %b %d %H:%M:%S +0000 %Y'),
        public=not tweetdata['user']['protected'],
        permalink_url='http://twitter.com/%s/status/%d'
            % (tweetdata['user']['screen_name'], tweetdata['id']),
        author=account_for_twitter_user(tweetdata['user']),
        in_reply_to=in_reply_to,
    )
    tweet.save()

    return False, tweet


def poll_twitter(account):
    user = account.person.user
    if user is None:
        return

    authtoken = account.authinfo
    if not authtoken:
        return

    # Get that twitter user's home timeline.
    csr = oauth.Consumer(*settings.TWITTER_CONSUMER)
    token = oauth.Token(*authtoken.split(':', 1))
    client = oauth.Client(csr, token)
    resp, content = client.request('http://api.twitter.com/1/statuses/home_timeline.json?include_entities=true&count=50', 'GET')
    if resp.status in (500, 502, 503):
        # Can't get Twitter results right now. Let's try again later.
        return
    if resp.status == 401:
        # The token may be invalid. Have we successfully scanned this account recently?
        if account.last_success > datetime.utcnow() - timedelta(days=2):
            raise ValueError("Token for Twitter user %s came back as invalid (possibly temporary)" % account.ident)
        # The token is now invalid (maybe they revoked the app). Stop updating this account.
        account.authinfo = ''
        account.save()
        raise ValueError("Token for Twitter user %s came back as invalid (probably permanent, so deleted authinfo)" % account.ident)
    if resp.status != 200:
        raise ValueError("Unexpected %d %s response fetching %s's twitter timeline"
            % (resp.status, resp.reason, account.ident))

    tl = json.loads(content)

    for orig_tweetdata in reversed(tl):
        try:
            # TODO: filter based on source?

            tweetdata = orig_tweetdata
            why_verb = 'post'
            try:
                tweetdata = orig_tweetdata['retweeted_status']
            except KeyError:
                pass
            else:
                why_verb = 'share'

            really_a_share, tweet = raw_object_for_tweet(tweetdata, client)
            if tweet is None:
                continue

            if really_a_share:
                why_verb = 'share'

            if why_verb == 'share':
                why_account = account_for_twitter_user(orig_tweetdata['user'])
            else:
                why_account = tweet.author

            # CASES:
            # real reply to...
            # real retweet of...
            # tweet with just a link
            # tweet with a link and custom text
            # tweet with a link and the link's target page title (found how?)

            if why_verb == 'post' and tweet.in_reply_to is not None:
                why_verb = 'reply'

            root = tweet
            while root.in_reply_to is not None:
                log.debug('Walking up from %r to %r', root, root.in_reply_to)
                root = root.in_reply_to

            streamitem, created = UserStream.objects.get_or_create(user=user, obj=root,
                # TODO: is tweet.time the right time here or do we need the "why time" from orig_tweetdata?
                defaults={'why_account': why_account, 'why_verb': why_verb, 'time': tweet.time})

            # Now add a reply for each tweet in the thread along the way.
            supertweet = tweet
            while supertweet.in_reply_to is not None:
                UserReplyStream.objects.get_or_create(user=user, root=root, reply=supertweet,
                    defaults={'root_time': streamitem.time, 'reply_time': supertweet.time})
                supertweet = supertweet.in_reply_to

        except Exception, exc:
            from sentry.client.base import SentryClient
            SentryClient().create_from_exception(view=__name__)
