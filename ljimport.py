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

import giraffe.friends.models
from giraffe.publisher.models import Asset


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Import posts from a livejournal XML export.')
    parser.add_argument('source', metavar='FILE', help='The filename of the XML export (or - for stdin)')
    parser.add_argument('--atomid', help='The prefix of the Atom ID to store', default=None)
    parser.add_argument('-v', dest='verbosity', action='append_const', const=1,
        help='Be more verbose (stackable)', default=[2])
    parser.add_argument('-q', dest='verbosity', action='append_const', const=-1,
        help='Be less verbose (stackable)')

    args = parser.parse_args(argv)

    verbosity = sum(args.verbosity)
    verbosity = 0 if verbosity < 0 else verbosity if verbosity < 4 else 4
    log_level = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][verbosity]
    logging.basicConfig(level=log_level)
    logging.info('Set log level to %s', logging.getLevelName(log_level))

    import_events(sys.stdin if args.source == '-' else args.source,
        args.atomid)

    return 0


def generate_openid(server_domain, username):
    if username.startswith('_'):
        return 'http://users.%s/%s/' % (server_domain, username)
    username = username.replace('_', '-')
    return 'http://%s.%s/' % (username, server_domain)


def import_events(source, atomid_prefix):
    tree = ElementTree.parse(source)

    username = tree.getroot().get('username')
    server = tree.getroot().get('server')
    server_domain = '.'.join(server.rsplit('.', 2)[1:])
    openid_for = partial(generate_openid, server_domain)
    if atomid_prefix is None:
        atomid_prefix = 'urn:lj:%s:atom1:%s:' % (server_domain, username)

    # First, update groups and friends, so we can knit the posts together right.
    group_objs = dict()
    for group in tree.findall('/friends/group'):
        id = group.findtext('id')
        name = group.findtext('name')

        tag = '%sgroup:%s' % (atomid_prefix, id)
        group_obj, created = giraffe.friends.models.Group.objects.get_or_create(tag=tag,
            defaults={'display_name': name})
        group_objs[id] = group_obj

    for friend in tree.findall('/friends/friend'):
        friendname = friend.findtext('username')
        openid = openid_for(friendname)

        ident_obj, created = giraffe.friends.models.Identity.objects.get_or_create(openid=openid)
        if created:
            # I guess we need to make a person for them too.
            person = giraffe.friends.models.Person()
            person.display_name = friend.findtext('fullname')
            person.save()
            ident_obj.person = person
            ident_obj.save()

        # Update their groups.
        group_objs = list(group_objs[groupid] for groupid in friend.findtext('group'))
        logging.debug("Setting %s's groups to %r", username, tuple(groupid for groupid in friend.findtext('group')))
        ident_obj.person.groups = group_objs

    # Import the posts.
    for event in tree.findall('/events/event'):
        ditemid = event.get('ditemid')
        logging.debug('Parsing event %s', ditemid)
        atom_id = '%s%s' % (atomid_prefix, ditemid)

        post, created = Asset.objects.get_or_create(atom_id=atom_id)

        event_props = {}
        for prop in event.findall('props/prop'):
            key = prop.get('name')
            val = prop.get('value')
            event_props[key] = val

        post.title = event.findtext('subject') or ''

        publ = event.findtext('date')
        assert publ, 'event has no date :('
        publ_dt = datetime.strptime(publ, '%Y-%m-%d %H:%M:%S')
        # TODO: is this in the account's timezone or what?
        post.published = publ_dt

        content_root = BeautifulSoup(event.findtext('event'))
        # Add line breaks to the post if it's not preformatted.
        if not int(event_props.get('opt_preformatted', 0)):
            for el in content_root.findAll(text=lambda t: '\n' in t):
                if el.findParent(re.compile(r'pre|lj-raw|table')) is None:
                    new_content = el.string.replace('\n', '<br>\n')
                    el.replaceWith(BeautifulSoup(new_content))
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

        post.save()
        logging.info('Saved new post %s (%s) as #%d', ditemid, post.title, post.pk)


if __name__ == '__main__':
    sys.exit(main())
