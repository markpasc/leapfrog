#!/usr/bin/env python

from datetime import datetime
import logging
import sys
from xml.etree import ElementTree

import argparse

import giraffe.friends.models
from giraffe.publisher.models import Asset


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Import posts from a Vox Atom XML export.')
    parser.add_argument('source', metavar='FILE', help='The filename of the XML export (or - for stdin)')
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

    import_assets(sys.stdin if args.source == '-' else args.source)

    return 0


def import_assets(source):
    tree = ElementTree.parse(source)

    groups = dict()

    for asset_el in tree.findall('{http://www.w3.org/2005/Atom}entry'):
        # Skip comments this go-round.
        if asset_el.find('{http://purl.org/syndication/thread/1.0}in-reply-to') is not None:
            continue

        atom_id = asset_el.findtext('{http://www.w3.org/2005/Atom}id')
        logging.debug('Parsing asset %s', atom_id)

        try:
            asset = Asset.objects.get(atom_id=atom_id)
        except Asset.DoesNotExist:
            asset = Asset(atom_id=atom_id)

        asset.title = asset_el.findtext('{http://www.w3.org/2005/Atom}title')

        publ = asset_el.findtext('{http://www.w3.org/2005/Atom}published')
        publ_dt = datetime.strptime(publ, '%Y-%m-%dT%H:%M:%SZ')
        asset.published = publ_dt

        content_el = asset_el.find('{http://www.w3.org/2005/Atom}content')
        content_type = content_el.get('type')
        if content_type == 'html':
            asset.content = content_el.text
        elif content_type == 'xhtml':
            html_el = content_el.find('{http://www.w3.org/1999/xhtml}div')
            html = ''.join(ElementTree.tostring(el, 'utf8') for el in html_el.getchildren())
            asset.content = html

        asset.imported = True
        asset.save()
        logging.info('Saved new asset %s (%s) as #%d', atom_id, asset.title, asset.pk)

        asset_groups = list()
        privacies = asset_el.findall('{http://www.sixapart.com/ns/atom/privacy}privacy/{http://www.sixapart.com/ns/atom/privacy}allow')
        for privacy in privacies:
            assert privacy.get('policy') == 'http://www.sixapart.com/ns/atom/permissions#read', 'Privacy policy for post is not about reading :('
            group_ref = privacy.get('ref')
            if group_ref == 'http://www.sixapart.com/ns/atom/groups#everyone':
                # Ignore this one.
                continue
            try:
                group = groups[group_ref]
            except KeyError:
                group, created = giraffe.friends.models.Group.objects.get_or_create(tag=group_ref,
                    defaults={'display_name': privacy.get('name')})
                groups[group_ref] = group
            asset_groups.append(group)
        logging.debug('Assigning asset %s to %d groups', atom_id, len(asset_groups))
        asset.private_to = asset_groups

    # TODO: import comments
    # TODO: import friends?


if __name__ == '__main__':
    sys.exit(main())
