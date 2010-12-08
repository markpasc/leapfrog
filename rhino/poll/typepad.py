from datetime import datetime
import logging
from urlparse import urlparse

from BeautifulSoup import BeautifulSoup
from django.conf import settings
import oauth2 as oauth
import typd
from tidylib import tidy_fragment

from rhino.models import Object, Account, Person, UserStream, Media, UserReplyStream
import rhino.poll.embedlam


log = logging.getLogger(__name__)


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
                display_name=tp_user.display_name or tp_user.preferred_username,
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


def remove_reblog_boilerplate_from_obj(obj):
    # Remove reblog boilerplate too.
    soup = BeautifulSoup(obj.body)
    top_two = soup.findAll(recursive=False, limit=2)
    if len(top_two) < 2:
        return
    maybe_quote, maybe_p = top_two

    # Regardless of what the first thing is, if the second is a <p><small>, toss 'em.
    if maybe_p.name == 'p' and maybe_p.find(name='small'):
        maybe_p.extract()
        maybe_quote.extract()
    # Well, there's no <p><small>, but let's remove a leading blockquote anyway.
    elif maybe_quote.name == 'blockquote':
        maybe_quote.extract()
    else:
        return

    obj.body = unicode(soup)


def object_for_typepad_object(tp_obj):
    try:
        obj = Object.objects.get(service='typepad.com', foreign_id=tp_obj.url_id)
    except Object.DoesNotExist:
        pass
    else:
        log.debug("Reusing typepad object %r for asset %s", obj, tp_obj.url_id)
        return obj

    log.debug("Making new object for TypePad post %s by %s", tp_obj.url_id, tp_obj.author.display_name)

    author = account_for_typepad_user(tp_obj.author)
    body = tp_obj.rendered_content
    if not body and tp_obj.content:
        if tp_obj.text_format == 'html_convert_linebreaks':
            body = '\n\n'.join(u'<p>%s</p>' % t for t in tp_obj.content.split('\n\n'))
        else:
            body = tp_obj.content
    if body:
        body, errors = tidy_fragment(body)
    else:
        body = ''

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

    if getattr(tp_obj, 'in_reply_to', None) is not None:
        obj.in_reply_to = object_for_typepad_object(tp_obj.in_reply_to)
    elif getattr(tp_obj, 'reblog_of', None) is not None:
        obj.in_reply_to = object_for_typepad_object(tp_obj.reblog_of)
        remove_reblog_boilerplate_from_obj(obj)
    elif getattr(tp_obj, 'reblog_of_url', None) is not None:
        reblog_url = tp_obj.reblog_of_url
        try:
            in_reply_to = rhino.poll.embedlam.object_for_url(reblog_url)
        except ValueError, exc:
            in_reply_to = None
            log.error("Error making object from referent %s of %s's post %s", reblog_url, author.display_name, tp_obj.url_id)
            log.exception(exc)

        if in_reply_to is not None:
            obj.in_reply_to = in_reply_to
            remove_reblog_boilerplate_from_obj(obj)

    if tp_obj.object_type == 'Photo':
        height, width = tp_obj.image_link.height, tp_obj.image_link.width
        image_url = tp_obj.image_link.url
        if tp_obj.image_link.url_template:
            if height > 1024 or width > 1024:
                # Use the 1024pi version.
                image_url = tp_obj.image_link.url_template.replace('{spec}', '1024pi')
                if height > width:
                    width = int(1024 * width / height)
                    height = 1024
                else:
                    height = int(1024 * height / width)
                    width = 1024

        image = Media(
            image_url=image_url,
            height=height,
            width=width,
        )
        image.save()

        obj.image = image
        obj.render_mode = 'image'

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
            if getattr(obj, 'in_reply_to', None) is not None:
                note.verb = 'Comment'

                superobj = obj
                while getattr(superobj, 'in_reply_to', None) is not None:
                    if superobj.root.object_type == 'Comment':
                        superobj.root, superobj.in_reply_to = superobj.in_reply_to, superobj.root
                    superobj.in_reply_to = t.assets.get(superobj.in_reply_to.url_id)
                    superobj = superobj.in_reply_to

            elif getattr(obj, 'reblog_of', None) is not None:
                note.verb = 'Reblog'

                reblog = obj
                while getattr(reblog, 'reblog_of', None) is not None:
                    reblog.reblog_of = t.assets.get(obj.reblog_of.url_id)
                    reblog = reblog.reblog_of

        if note.verb == 'NewAsset':
            okay_types = ['Post']
            if obj.container and obj.container.object_type == 'Group':
                okay_types.extend(['Photo', 'Audio', 'Video', 'Link'])
            if obj.object_type not in okay_types:
                continue

        # Yay, let's show this one!
        yield note


def object_from_url(url):
    # We're using an action endpoint anyway, so the oauth2.Client will work here.
    csr = oauth.Consumer(*settings.TYPEPAD_CONSUMER)
    token = oauth.Token(*settings.TYPEPAD_ANONYMOUS_ACCESS_TOKEN)
    cl = oauth.Client(csr, token)
    t = typd.TypePad(endpoint='https://api.typepad.com/', client=cl)

    urlparts = urlparse(url)
    try:
        result = t.domains.resolve_path(id=urlparts.netloc, path=urlparts.path)
    except typd.NotFound, exc:
        raise ValueError("TypePad could not resolve URL %s: %s" % (url, str(exc)))
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
        try:
            obj = object_for_typepad_object(note.object)

            root = obj
            while root.in_reply_to is not None:
                root = root.in_reply_to

            if not UserStream.objects.filter(user=user, obj=root).exists():
                actor = account_for_typepad_user(note.actor)
                why_verb = {
                    'AddedFavorite': 'like',
                    'NewAsset': 'post' if obj is root else 'share',
                    'Comment': 'reply',
                    'Reblog': 'share',
                }[note.verb]
                UserStream.objects.create(user=user, obj=root,
                    time=note.published,
                    why_account=actor, why_verb=why_verb)

            superobj = obj
            while superobj.in_reply_to is not None:
                UserReplyStream.objects.get_or_create(user=user, root=root, reply=superobj,
                    defaults={'root_time': root.time, 'reply_time': superobj.time})
                superobj = superobj.in_reply_to

        except Exception, exc:
            log.exception(exc)
