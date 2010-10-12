from datetime import datetime
import json
import logging
import re

from django.conf import settings
import oauth2 as oauth

from rhino.models import Object, Account, Person, UserStream, Media, UserReplyStream
from rhino.poll.embedlam import object_for_url


log = logging.getLogger(__name__)


def account_for_twitter_user(userdata):
    try:
        account = Account.objects.get(service='twitter.com', ident=str(userdata['id']))
    except Account.DoesNotExist:
        avatar = Media(
            width=48,
            height=48,
            image_url=userdata['profile_image_url'],
        )
        avatar.save()
        person = Person(
            display_name=userdata['name'],
            avatar=avatar,
        )
        person.save()
        account = Account(
            service='twitter.com',
            ident=str(userdata['id']),
            display_name=userdata['name'],
            person=person,

            status_background_color=userdata['profile_background_color'],
            status_background_image_url=userdata['profile_background_image_url'],
            status_background_tile=userdata['profile_background_tile'],
        )
        account.save()

    return account


def tweet_html(tweetdata):
    tweet = tweetdata['text']
    if 'entities' not in tweetdata:
        return tweet

    mutations = list()
    for urldata in tweetdata['entities'].get('urls', ()):
        url = urldata['expanded_url'] or urldata['url']
        mutations.append({
            'indices': urldata['indices'],
            'html': """<a href="%s">%s</a>""" % (url, url),
        })
    for mentiondata in tweetdata['entities'].get('user_mentions', ()):
        mutations.append({
            'indices': mentiondata['indices'],
            'html': """@<a href="http://twitter.com/%(screen_name)s" title="%(name)s">%(screen_name)s</a>""" % mentiondata,
        })
    for tagdata in tweetdata['entities'].get('hashtags', ()):
        mutations.append({
            'indices': tagdata['indices'],
            'html': """<a href="http://twitter.com/search?q=%%23%(text)s">#%(text)s</a>""" % tagdata,
        })

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


def raw_object_for_tweet(tweetdata, client):
    try:
        return Object.objects.get(service='twitter.com', foreign_id=str(tweetdata['id']))
    except Object.DoesNotExist:
        pass

    log.debug('Making new tweet for %s status #%d', tweetdata['user']['screen_name'], tweetdata['id'])

    in_reply_to = None
    if tweetdata.get('in_reply_to_status_id'):
        # Uh oh, gotta get that tweet.
        # TODO: remove the mention from the front of the tweet
        next_tweetid = tweetdata['in_reply_to_status_id']
        try:
            in_reply_to = Object.objects.get(service='twitter.com', foreign_id=str(next_tweetid))
        except Object.DoesNotExist:
            resp, content = client.request('http://api.twitter.com/1/statuses/show/%d.json'
                % next_tweetid)
            if resp.status != 200:
                raise ValueError("Unexpected %d %s response fetching tweet #%s up a reply chain for "
                    "%s's timeline" % (resp.status, resp.reason, next_tweetid, account.display_name))

            next_tweetdata = json.loads(content)
            synthesize_entities(next_tweetdata)
            log.debug("    Let's make a new tweet for %s status #%d", next_tweetdata['user']['screen_name'], next_tweetdata['id'])
            in_reply_to = raw_object_for_tweet(next_tweetdata, client)

    # Is this something other than a status?
    if len(tweetdata['entities']['urls']) == 1:
        about_urldata = tweetdata['entities']['urls'][0]
        about_url = about_urldata['expanded_url'] or about_urldata['url']

        try:
            in_reply_to = object_for_url(about_url)
        except ValueError, exc:
            log.debug(str(exc))

    tweet = Object(
        service='twitter.com',
        foreign_id=str(tweetdata['id']),
        render_mode='status',
        body=tweet_html(tweetdata),
        time=datetime.strptime(tweetdata['created_at'], '%a %b %d %H:%M:%S +0000 %Y'),
        permalink_url='http://twitter.com/%s/status/%d'
            % (tweetdata['user']['screen_name'], tweetdata['id']),
        author=account_for_twitter_user(tweetdata['user']),
        in_reply_to=in_reply_to,
    )
    tweet.save()

    return tweet


def poll_twitter(account):
    user = account.person.user
    if user is None:
        return

    # Get that twitter user's home timeline.
    csr = oauth.Consumer(*settings.TWITTER_CONSUMER)
    token = oauth.Token(*account.authinfo.split(':', 1))
    client = oauth.Client(csr, token)
    resp, content = client.request('http://api.twitter.com/1/statuses/home_timeline.json?include_entities=true', 'GET')
    if resp.status != 200:
        raise ValueError("Unexpected %d %s response fetching %s's twitter timeline"
            % (resp.status, resp.reason, account.display_name))

    tl = json.loads(content)
    from pprint import pformat
    log.debug(pformat(tl))

    for orig_tweetdata in reversed(tl):
        # TODO: filter based on source?

        tweetdata = orig_tweetdata
        why_verb = 'post'
        try:
            tweetdata = orig_tweetdata['retweeted_status']
        except KeyError:
            pass
        else:
            why_verb = 'share'

        orig_actor = account_for_twitter_user(orig_tweetdata['user'])
        tweet = raw_object_for_tweet(tweetdata, client)

        # CASES:
        # real reply to...
        # real retweet of...
        # tweet with just a link
        # tweet with a link and custom text
        # tweet with a link and the link's target page title (found how?)

        if why_verb == 'post' and not tweet.in_reply_to:
            UserStream.objects.get_or_create(user=user, obj=tweet,
                defaults={'why_account': tweet.author, 'why_verb': 'post', 'time': tweet.time})

        # But if it's really a reply?
        elif why_verb == 'post':
            root = tweet
            while root.in_reply_to is not None:
                log.debug('Walking up from %r to %r', root, root.in_reply_to)
                root = root.in_reply_to

            UserStream.objects.get_or_create(user=user, obj=root,
                defaults={'why_account': tweet.author, 'why_verb': 'reply', 'time': tweet.time})
            UserReplyStream.objects.get_or_create(user=user, root=root, reply=tweet,
                defaults={'root_time': root.time, 'reply_time': tweet.time})

        elif why_verb == 'share':
            # Sharing is transitive, so really share the root.
            root = tweet
            while root.in_reply_to is not None:
                log.debug('Walking up from %r to %r', root, root.in_reply_to)
                root = root.in_reply_to

            UserStream.objects.get_or_create(user=user, obj=root,
                defaults={'why_account': orig_actor, 'why_verb': 'share', 'time': tweet.time})
