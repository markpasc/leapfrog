#!/usr/bin/env python

from datetime import datetime
import logging
import re
import sys
from xml.etree import ElementTree

import argparse
from BeautifulSoup import BeautifulSoup, NavigableString
import django

from giraffe.publisher.models import Asset


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Import posts from a livejournal XML export.')
    parser.add_argument('source', metavar='FILE', help='The filename of the XML export (or - for stdin)')
    parser.add_argument('--atomid', help='The prefix of the Atom ID to store')
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


def import_events(source, atomid_prefix):
    tree = ElementTree.parse(source)

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
            for child in reversed(el.contents):
                el_parent.insert(my_index, child)
        # TODO: handle opt_nocomments prop
        # TODO: put music and mood in the post content
        # TODO: handle taglist prop
        post.content = content_root.prettify()

        post.save()
        logging.info('Saved new post %s (%s) as #%d', ditemid, post.title, post.pk)


if __name__ == '__main__':
    sys.exit(main())
