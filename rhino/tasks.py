from datetime import datetime
import json

from django.conf import settings
import oauth2 as oauth

from rhino.models import Object, Account, Person, UserStream


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

    for orig_tweetdata in tl:
        try:
            tweetdata = orig_tweetdata['retweeted_status']
        except KeyError:
            tweetdata = orig_tweetdata
            retweet = False
        else:
            retweet = True

        # Who is the author?
        try:
            author = Account.objects.get(service='twitter.com', ident=str(tweetdata['user']['id']))
        except Account.DoesNotExist:
            person = Person(
                display_name=tweetdata['user']['name'],
            )
            person.save()
            author = Account(
                service='twitter.com',
                ident=str(tweetdata['user']['id']),
                display_name=tweetdata['user']['name'],
                person=person,
            )
            author.save()

        try:
            tweet = Object.objects.get(service='twitter.com', foreign_id=str(tweetdata['id']))
        except Object.DoesNotExist:
            # TODO: twitpics etc are photos
            tweet = Object(
                service='twitter.com',
                foreign_id=str(tweetdata['id']),
                render_mode='status',
                body=tweetdata['text'],
                time=datetime.strptime(tweetdata['created_at'], '%a %b %d %H:%M:%S +0000 %Y'),
                permalink_url='http://twitter.com/%s/status/%d'
                    % (tweetdata['user']['screen_name'], tweetdata['id']),
                author=author,
            )
            tweet.save()

        if UserStream.objects.filter(user=user, obj=tweet).exists():
            continue

        if not retweet:
            UserStream.objects.create(user=user, obj=tweet,
                why_account=author, why_verb='post')
            continue

        try:
            retweeter = Account.objects.get(service='twitter.com', ident=str(orig_tweetdata['user']['id']))
        except Account.DoesNotExist:
            person = Person(
                display_name=orig_tweetdata['user']['name'],
            )
            person.save()
            retweeter = Account(
                service='twitter.com',
                ident=str(orig_tweetdata['user']['id']),
                display_name=orig_tweetdata['user']['id'],
                person=person,
            )
            retweeter.save()

        UserStream.objects.create(user=user, obj=tweet,
            why_account=retweeter, why_verb='share')
