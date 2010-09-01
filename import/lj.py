#!/usr/bin/env python

from datetime import datetime
from functools import partial
import logging
import re
import sys
from xml.etree import ElementTree

import argparse
from BeautifulSoup import BeautifulSoup, NavigableString
import django
from django.contrib.auth.models import User

import giraffe.friends.models
from giraffe.publisher.models import Asset


foaf_names = dict()
foaf_pics = dict()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Import posts from a livejournal XML export.')
    parser.add_argument('source', metavar='FILE', help='The filename of the XML export (or - for stdin)')
    parser.add_argument('--foaf', metavar='FILE', help='The filename of the FOAF document from which to pull friend names and userpic URLs')
    parser.add_argument('--atomid', help='The prefix of the Atom ID to store', default=None)
    parser.add_argument('-v', dest='verbosity', action='append_const', const=1,
        help='Be more verbose (stackable)', default=[2])
    parser.add_argument('-q', dest='verbosity', action='append_const', const=-1,
        help='Be less verbose (stackable)')

    args = parser.parse_args(argv)

    verbosity = sum(args.verbosity)
    verbosity = 0 if verbosity < 0 else verbosity if verbosity < 4 else 4
    log_level = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][verbosity]
    logging.getLogger().setLevel(level=log_level)
    logging.info('Set log level to %s', logging.getLevelName(log_level))

    import_events(sys.stdin if args.source == '-' else args.source,
        args.atomid, args.foaf)

    return 0


def generate_openid(server_domain, username):
    if username.startswith('_'):
        return 'http://users.%s/%s/' % (server_domain, username)
    username = username.replace('_', '-')
    return 'http://%s.%s/' % (username, server_domain)


def import_foaf(source, server_domain):
    tree = ElementTree.parse(source)
    logging.debug('Yay processing a FOAF document!')

    for person in tree.findall('//{http://xmlns.com/foaf/0.1/}Person'):
        nick = person.findtext('{http://xmlns.com/foaf/0.1/}nick')
        logging.debug('Processing FOAF sack for %s', nick)
        name = person.findtext('{http://xmlns.com/foaf/0.1/}member_name') or ''
        pic = person.findtext('{http://xmlns.com/foaf/0.1/}image') or ''

        openid = generate_openid(server_domain, nick)
        foaf_names[openid] = name
        foaf_pics[openid] = pic


def person_for_openid(openid, display_name=None, userpic_url=None):
    if display_name is None:
        display_name = foaf_names.get(openid, '')
    if userpic_url is None:
        userpic_url = foaf_pics.get(openid, '')

    try:
        ident_obj = giraffe.friends.models.Identity.objects.get(openid=openid)
    except giraffe.friends.models.Identity.DoesNotExist:
        # Who? I guess we need to make a Person too.
        person = giraffe.friends.models.Person(
            display_name=display_name,
            profile_url=openid,
            userpic_url=userpic_url,
        )
        person.save()
        ident_obj = giraffe.friends.models.Identity(openid=openid, person=person)
        ident_obj.save()
    else:
        person = ident_obj.person
        if not person.profile_url or not person.userpic_url:
            if not person.profile_url:
                person.profile_url = openid
            if not person.userpic_url:
                person.userpic_url = userpic_url
            person.save()

    return person


def make_my_openid(openid):
    person = User.objects.all().order_by('id')[0].person
    try:
        ident = giraffe.friends.models.Identity.objects.get(openid=openid)
    except giraffe.friends.models.Identity.DoesNotExist:
        logging.info('Creating new identity mapping to %s for %s', person.display_name, openid)
        ident = giraffe.friends.models.Identity(openid=openid, person=person)
        ident.save()
    else:
        if ident.person.pk == person.pk:
            logging.debug('Identity %s is already yours, yay', openid)
        else:
            logging.info('Merging existing person %s for identity %s into person %s',
                ident.person.display_name, openid, person.display_name)
            ident.person.merge_into(person)

    return person


def format_soup(content_root):
    for el in content_root.findAll(text=lambda t: '\n' in t):
        if el.findParent(re.compile(r'pre|lj-raw|table')) is None:
            new_content = el.string.replace('\n', '<br>\n')
            el.replaceWith(BeautifulSoup(new_content))


def import_comment(comment_el, asset, openid_for):
    jtalkid = comment_el.get('jtalkid')
    atom_id = '%s:talk:%s' % (asset.atom_id, jtalkid)
    logging.debug('Yay importing comment %s', jtalkid)

    try:
        comment = Asset.objects.get(atom_id=atom_id)
    except Asset.DoesNotExist:
        comment = Asset(atom_id=atom_id)

    comment_props = {}
    for prop in comment_el.findall('props/prop'):
        key = prop.get('name')
        val = prop.get('value')
        comment_props[key] = val

    comment.title = comment_el.findtext('subject') or ''

    body = comment_el.findtext('body')
    if int(comment_props.get('opt_preformatted') or 0):
        comment.content = body
    else:
        logging.debug("    Oops, comment not preformatted, let's parse it")
        content_root = BeautifulSoup(body)
        format_soup(content_root)
        comment.content = str(content_root)

    comment.in_reply_to = asset
    comment.in_thread_of = asset.in_thread_of or asset

    poster = comment_el.get('poster')
    if poster:
        openid = openid_for(poster)
        logging.debug("    Saving %s as comment author", openid)
        comment.author = person_for_openid(openid)
    else:
        logging.debug("    Oh huh this comment was anonymous, fancy that")

    comment.imported = True
    comment.save()

    comment.private_to = asset.private_to.all()

    for reply_el in comment_el.findall('comments/comment'):
        import_comment(reply_el, comment, openid_for)


def import_events(source, atomid_prefix, foafsource):
    tree = ElementTree.parse(source)

    username = tree.getroot().get('username')
    server = tree.getroot().get('server')
    server_domain = '.'.join(server.rsplit('.', 2)[1:])
    openid_for = partial(generate_openid, server_domain)
    if atomid_prefix is None:
        atomid_prefix = 'urn:lj:%s:atom1:%s:' % (server_domain, username)

    post_author = make_my_openid(openid_for(username))

    # First, if there's a FOAF, learn all my friends' names and faces.
    if foafsource:
        import_foaf(foafsource, server_domain)

    # Now update groups and friends, so we can knit the posts together right.
    group_objs = dict()
    for group in tree.findall('/friends/group'):
        id = int(group.findtext('id'))
        name = group.findtext('name')

        tag = '%sgroup:%d' % (atomid_prefix, id)
        group_obj, created = giraffe.friends.models.Group.objects.get_or_create(tag=tag,
            defaults={'display_name': name})
        group_objs[id] = group_obj

    all_friends_tag = '%sfriends' % atomid_prefix
    all_friends_group, created = giraffe.friends.models.Group.objects.get_or_create(
        tag=all_friends_tag, defaults={'display_name': 'Friends'})

    for friend in tree.findall('/friends/friend'):
        friendname = friend.findtext('username')
        openid = openid_for(friendname)

        ident_person = person_for_openid(openid, friend.findtext('fullname'))

        # Update their groups.
        group_ids = tuple(int(groupnode.text) for groupnode in friend.findall('groups/group'))
        logging.debug("Setting %s's groups to %r", friendname, group_ids)
        ident_person.groups = [all_friends_group] + [group_objs[id] for id in group_ids]

    # Import the posts.
    for event in tree.findall('/events/event'):
        ditemid = event.get('ditemid')
        logging.debug('Parsing event %s', ditemid)
        atom_id = '%s%s' % (atomid_prefix, ditemid)

        try:
            post = Asset.objects.get(atom_id=atom_id)
        except Asset.DoesNotExist:
            post = Asset(atom_id=atom_id)

        event_props = {}
        for prop in event.findall('props/prop'):
            key = prop.get('name')
            val = prop.get('value')
            event_props[key] = val

        post.title = event.findtext('subject') or ''
        post.author = post_author

        publ = event.findtext('date')
        assert publ, 'event has no date :('
        publ_dt = datetime.strptime(publ, '%Y-%m-%d %H:%M:%S')
        # TODO: is this in the account's timezone or what?
        post.published = publ_dt

        content_root = BeautifulSoup(event.findtext('event'))
        # Add line breaks to the post if it's not preformatted.
        if not int(event_props.get('opt_preformatted', 0)):
            format_soup(content_root)
        # Remove any lj-raw tags.
        for el in content_root.findAll(re.compile(r'lj-(?:raw|cut)')):
            # Replace it with its children.
            el_parent = el.parent
            el_index = el_parent.contents.index(el)
            el.extract()
            for child in reversed(list(el.contents)):
                el_parent.insert(el_index, child)
        # TODO: handle opt_nocomments prop
        # TODO: put music and mood in the post content
        # TODO: handle taglist prop
        post.content = str(content_root)

        post.imported = True
        post.save()
        logging.info('Saved new post %s (%s) as #%d', ditemid, post.title, post.pk)

        security = event.get('security')
        private_group = giraffe.friends.models.Group.objects.get(tag='private')
        if security == 'private':
            logging.debug('Oh ho post %s is all fancy private', ditemid)
            post.private_to = [private_group]
        elif security == 'usemask':
            bin = lambda s: str(s) if s<=1 else bin(s>>1) + str(s&1)

            mask = int(event.get('allowmask'))
            logging.debug('Post %s has mask %s?', ditemid, bin(mask))

            if mask == 1:
                mask_groups = [all_friends_group]
                # Plus all the other bits are 0, so we'll add no other groups.
            else:
                mask_groups = list()

            for i in range(1, 30):
                mask = mask >> 1
                if mask == 0:
                    break
                logging.debug('    Remaining mask %s', bin(mask))
                if mask & 0x01:
                    logging.debug('    Yay %s has group %d!', ditemid, i)
                    if i in group_objs:
                        logging.debug('    And group %d exists woohoo!!', i)
                        mask_groups.append(group_objs[i])

            logging.debug('So post %s gets %d groups', ditemid, len(mask_groups))
            post.private_to = mask_groups

        # Import the comments.
        for comment in event.findall('comments/comment'):
            import_comment(comment, post, openid_for)


if __name__ == '__main__':
    sys.exit(main())
