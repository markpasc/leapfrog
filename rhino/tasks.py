from django.conf import settings
import oauth2 as oauth

from rhino.models import Object


def poll_twitter(account):
    # Get that twitter user's home timeline.
    csr = oauth.Consumer(*settings.TWITTER_CONSUMER)
    token = oauth.Token(*account.authinfo.split(':', 1))
    client = oauth.Client(csr, token)
    resp, content = client.request('http://api.twitter.com/1/status/home_timeline.json?include_entities=true', 'GET')
    if resp.status != 200:
        raise ValueError("Unexpected %d %s response fetching %s's twitter timeline"
            % (resp.status, resp.reason, account.display_name))

    tl = json.loads(content)

    for tweetdata in tl:
        # Who is the author?
        author = ...

        try:
            tweet = Object.objects.get(service='twitter.com', foreign_id=str(tweetdata['id']))
        except Object.DoesNotExist:
            tweet = Object(
                object_type='status',
                summary=tweetdata['text'],
                content=tweetdata['text'],
                permalink_url='http://twitter.com/%s/status/%d'
                    % (tweetdata['user']['screen_name'], tweetdata['id']),
                author=author,
            )
            tweet.save()

        # TODO: replies are replies

        UserStream.objects.get_or_create(who=account.who, obj=tweet)
