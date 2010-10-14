from datetime import datetime
import logging
from urlparse import urlparse

from django.conf import settings
import oauth2 as oauth
import typd
from tidylib import tidy_fragment

from rhino.models import Object, Account, Person, UserStream, Media, UserReplyStream


def account_for_typepad_user(tp_user, person=None):
    try:
        account = Account.objects.get(service='typepad.com', ident=tp_user.url_id)
    except Account.DoesNotExist:
        if person is None:
            if tp_user.avatar_link.url_template:
                avatar = Media(
                    width=50,
                    height=50,
                    image_url=tp_user.avatar_link.url_template.replace('{spec}', '50si'),
                )
            else:
                avatar = Media(
                    width=tp_user.avatar_link.width,
                    height=tp_user.avatar_link.height,
                    image_url=tp_user.avatar_link.url,
                )
            avatar.save()
            person = Person(
                display_name=tp_user.display_name,
                avatar=avatar,
                permalink_url=tp_user.profile_page_url,
            )
            person.save()
        account = Account(
            service='typepad.com',
            ident=tp_user.url_id,
            display_name=tp_user.display_name,
            person=person,
        )
        account.save()

    return account


def object_for_typepad_object(tp_obj):
    try:
        obj = Object.objects.get(service='typepad.com', foreign_id=tp_obj.url_id)
    except Object.DoesNotExist:
        author = account_for_typepad_user(tp_obj.author)
        body = tp_obj.rendered_content or tp_obj.content or ''
        if body:
            body, errors = tidy_fragment(body)
        obj = Object(
            service='typepad.com',
            foreign_id=tp_obj.url_id,
            render_mode='mixed',
            title=tp_obj.title,
            body=body,
            time=tp_obj.published,
            permalink_url=tp_obj.permalink_url,
            author=author,
        )
        obj.save()

    return obj


def good_notes_for_notes(notes, t):
    for note in notes:
        # TODO: skip notes when paging

        if note.verb in ('AddedNeighbor', 'SharedBlog', 'JoinedGroup'):
            continue

        obj = note.object

        if obj is None:  # deleted asset
            continue
        if obj.permalink_url is None:  # no ancillary
            continue
        if obj.source is not None:  # no boomerang
            if obj.source.by_user:
                continue
        if obj.container is not None and obj.container.url_id in ('6p0120a5e990ac970c', '6a013487865036970c0134878650f2970c'):
            continue

        if note.verb == 'NewAsset':
            if getattr(obj, 'root', None) is not None:
                note.original = obj
                note.verb = 'Comment'
                obj = note.object = t.assets.get(obj.root.url_id)

            if getattr(obj, 'reblog_of', None) is not None:
                note.original = obj
                note.verb = 'Reblog'

        if note.verb == 'NewAsset':
            okay_types = ['Post']
            if obj.container and obj.container.object_type == 'Group':
                okay_types.extend(['Photo', 'Audio', 'Video', 'Link'])
            if obj.object_type not in okay_types:
                continue

        # Move all reactions up to the root object of reblogging.
        while getattr(obj, 'reblog_of', None) is not None:
            obj = note.object = t.assets.get(obj.reblog_of.url_id)

        # Yay, let's show this one!
        yield note


def object_from_url(url):
    # We're using an action endpoint anyway, so the oauth2.Client will work here.
    csr = oauth.Consumer(*settings.TYPEPAD_CONSUMER)
    token = oauth.Token(*settings.TYPEPAD_ANONYMOUS_ACCESS_TOKEN)
    cl = oauth.Client(csr, token)
    t = typd.TypePad(endpoint='https://api.typepad.com/', client=cl)

    urlparts = urlparse(url)
    result = t.domains.resolve_path(id=urlparts.netloc, path=urlparts.path)
    if result.is_full_match and result.asset:
        return object_for_typepad_object(result.asset)

    raise ValueError("Could not identify TypePad asset for url %s" % url)


def poll_typepad(account):
    user = account.person.user
    if user is None:
        return

    # Get that TypePad user's notifications.
    t = typd.TypePad(endpoint='http://api.typepad.com/')
    notes = t.users.get_notifications(account.ident)

    for note in good_notes_for_notes(reversed(notes.entries), t):
        obj = object_for_typepad_object(note.object)

        # TODO: mangle reblogs into shares or replies

        if not UserStream.objects.filter(user=user, obj=obj).exists():
            actor = account_for_typepad_user(note.actor)
            why_verb = {
                'AddedFavorite': 'like',
                'NewAsset': 'post',
                'Comment': 'reply',
                'Reblog': 'reply',
            }[note.verb]
            UserStream.objects.create(user=user, obj=obj,
                time=note.published,
                why_account=actor, why_verb=why_verb)

        if note.verb in ('Comment', 'Reblog'):
            reply = object_for_typepad_object(note.original)
            UserReplyStream.objects.get_or_create(user=user, root=obj, reply=reply,
                defaults={'root_time': obj.time, 'reply_time': reply.time})
