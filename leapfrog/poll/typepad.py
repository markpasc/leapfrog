from datetime import datetime
import logging
from urlparse import urlparse

from BeautifulSoup import BeautifulSoup
from django.conf import settings
import oauth2 as oauth
import typd
from tidylib import tidy_fragment

from leapfrog.models import Object, Account, Person, UserStream, Media, UserReplyStream
import leapfrog.poll.embedlam


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
            display_name=tp_user.display_name or tp_user.preferred_username,
            person=person,
        )
        account.save()
    else:
        person = account.person
        if not person.avatar_source or person.avatar_source == 'typepad.com':
            if tp_user.avatar_link.url_template:
                tp_avatar_url = tp_user.avatar_link.url_template.replace('{spec}', '50si')
            else:
                tp_avatar_url = tp_user.avatar_link.url

            if not person.avatar or person.avatar.image_url != tp_avatar_url:
                if tp_user.avatar_link.url_template:
                    avatar = Media(
                        width=50,
                        height=50,
                        image_url=tp_avatar_url,
                    )
                else:
                    avatar = Media(
                        width=tp_user.avatar_link.width,
                        height=tp_user.avatar_link.height,
                        image_url=tp_avatar_url,
                    )
                avatar.save()
                person.avatar = avatar
                person.avatar_source = 'typepad.com'
                person.save()
            elif not person.avatar_source:
                person.avatar_source = 'typepad.com'
                person.save()

    return account


def remove_reblog_boilerplate_from_obj(obj):
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

    obj.body = str(soup).decode('utf8').strip()


def object_for_typepad_object(tp_obj):
    try:
        obj = Object.objects.get(service='typepad.com', foreign_id=tp_obj.url_id)
    except Object.DoesNotExist:
        pass
    else:
        log.debug("Reusing typepad object %r for asset %s", obj, tp_obj.url_id)
        return False, obj

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
        # This post is in reply, so we don't care if our referent was
        # really a share. Be transitively in reply to the shared obj.
        really_a_share, obj.in_reply_to = object_for_typepad_object(tp_obj.in_reply_to)
    elif getattr(tp_obj, 'reblog_of', None) is not None:
        # Assets are public so it's okay if we use an anonymous typd here.
        t = typd.TypePad(endpoint='http://api.typepad.com/')
        reblog_of = t.assets.get(tp_obj.reblog_of.url_id)

        really_a_share, obj.in_reply_to = object_for_typepad_object(reblog_of)
        remove_reblog_boilerplate_from_obj(obj)
        if not obj.body:
            return True, obj.in_reply_to
    elif getattr(tp_obj, 'reblog_of_url', None) is not None:
        reblog_url = tp_obj.reblog_of_url
        try:
            in_reply_to = leapfrog.poll.embedlam.object_for_url(reblog_url)
        except leapfrog.poll.embedlam.RequestError, exc:
            in_reply_to = None
        except ValueError, exc:
            in_reply_to = None
            log.error("Error making object from referent %s of %s's post %s", reblog_url, author.display_name, tp_obj.url_id)
            log.exception(exc)

        if in_reply_to is not None:
            obj.in_reply_to = in_reply_to
            remove_reblog_boilerplate_from_obj(obj)
            if not obj.body:
                return True, in_reply_to

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
    elif tp_obj.object_type == 'Video':
        obj.body = '\n\n'.join((tp_obj.video_link.embed_code, obj.body))

    obj.save()

    return False, obj


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
                    try:
                        superobj.in_reply_to = t.assets.get(superobj.in_reply_to.url_id)
                    except typd.Forbidden:
                        # Can we skip to the thread root?
                        if superobj.in_reply_to.url_id != superobj.root.url_id:
                            # Yep, try this superobj again with the root.
                            superobj.in_reply_to = superobj.root
                        else:
                            # No, the root itself is private. Guess we'll have to present the comment as top level.
                            break
                    else:
                        # Continuing walking up through the newly filled-in object.
                        superobj = superobj.in_reply_to

            elif getattr(obj, 'reblog_of', None) is not None:
                note.verb = 'Reblog'
            elif getattr(obj, 'reblog_of_url', None) is not None:
                note.verb = 'Reblog'

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
    cl.disable_ssl_certificate_validation = True
    t = typd.TypePad(endpoint='https://api.typepad.com/', client=cl)

    urlparts = urlparse(url)
    try:
        result = t.domains.resolve_path(id=urlparts.netloc, path=urlparts.path)
    except KeyError, exc:
        if str(exc) == 'Generic':
            # A link to an uploaded file (so our typd couldn't make a result asset), so let's ignore it.
            return
        raise
    except (typd.NotFound, typd.Unauthorized), exc:
        raise ValueError("TypePad could not resolve URL %s: %s" % (url, str(exc)))
    if result.is_full_match and result.asset:
        really_a_share, obj = object_for_typepad_object(result.asset)
        return obj

    raise ValueError("Could not identify TypePad asset for url %s" % url)


def poll_typepad(account):
    user = account.person.user
    if user is None:
        return

    # Get that TypePad user's notifications.
    t = typd.TypePad(endpoint='http://api.typepad.com/')
    notes = t.users.get_notifications(account.ident)
    try:
        notes.entries
    except typd.ServerError:
        # Guess we can't get those notes right now.
        return

    for note in good_notes_for_notes(reversed(notes.entries), t):
        try:
            really_a_share, obj = object_for_typepad_object(note.object)

            root = obj
            while root.in_reply_to is not None:
                root = root.in_reply_to

            try:
                streamitem = UserStream.objects.get(user=user, obj=root)
            except UserStream.DoesNotExist:
                actor = account_for_typepad_user(note.actor)
                why_verb = {
                    'AddedFavorite': 'like',
                    'NewAsset': 'post' if obj is root and not really_a_share else 'share',
                    'Comment': 'reply',
                    'Reblog': 'share',
                }[note.verb]
                streamitem = UserStream.objects.create(user=user, obj=root,
                    time=note.published, why_account=actor, why_verb=why_verb)

            superobj = obj
            while superobj.in_reply_to is not None:
                UserReplyStream.objects.get_or_create(user=user, root=root, reply=superobj,
                    defaults={'root_time': streamitem.time, 'reply_time': superobj.time})
                superobj = superobj.in_reply_to

        except Exception, exc:
            log.exception(exc)
