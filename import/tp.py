#!/usr/bin/env python

import logging
import sys

import argparse
from oauth.oauth import OAuthConsumer, OAuthToken
from django.contrib.auth.models import User
import typepad

import giraffe.friends.models
from giraffe.publisher.models import Asset


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description='Import posts from a livejournal XML export.')
    parser.add_argument('--atomid', help='The prefix of the Atom ID to store', default=None)
    parser.add_argument('--consumer', help='The consumer token to use (:-separated)', required=True)
    parser.add_argument('--access', help='The access token to use (:-separated)', required=True)
    parser.add_argument('--blog', help='The ID of the blog to import', required=True)
    parser.add_argument('-v', dest='verbosity', action='append_const', const=1,
        help='Be more verbose (stackable)', default=[2])
    parser.add_argument('-q', dest='verbosity', action='append_const', const=-1,
        help='Be less verbose (stackable)')

    args = parser.parse_args(argv)

    verbosity = sum(args.verbosity)
    verbosity = 0 if verbosity < 0 else verbosity if verbosity < 4 else 4
    log_level = [logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][verbosity]
    logging.getLogger().setLevel(level=log_level)
    for logspace in ('batchhttp', 'typepad'):
        logging.getLogger(logspace).setLevel(level=logging.WARNING)
    logging.info('Set log level to %s', logging.getLevelName(log_level))

    typepad.client.add_credentials(OAuthConsumer(*args.consumer.split(':')),
        OAuthToken(*args.access.split(':')), domain='api.typepad.com')
    logging.debug('Configurated with oauthness')

    import_me()
    import_blog(args.blog)

    return 0


def import_me():
    me = typepad.User.get_self()
    openid = me.profile_page_url
    assert openid, 'I have no profile page url :('

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


def person_for_openid(openid, display_name):
    try:
        ident_obj = giraffe.friends.models.Identity.objects.get(openid=openid)
    except giraffe.friends.models.Identity.DoesNotExist:
        # Who? I guess we need to make a Person too.
        person = giraffe.friends.models.Person()
        person.display_name = display_name
        person.save()
        ident_obj = giraffe.friends.models.Identity(openid=openid)
        ident_obj.person = person
        ident_obj.save()

    return ident_obj.person


def format_soup(content_root):
    for el in content_root.findAll(text=lambda t: '\n' in t):
        if el.findParent(re.compile(r'pre|lj-raw|table')) is None:
            new_content = el.string.replace('\n', '<br>\n')
            el.replaceWith(BeautifulSoup(new_content))


def import_assets(assets):
    for tpasset in assets:
        logging.debug('Parsing asset %s', tpasset.url_id)
        try:
            asset = Asset.objects.get(atom_id=tpasset.id)
        except Asset.DoesNotExist:
            asset = Asset(atom_id=tpasset.id)
        asset.imported = True

        if tpasset.author and tpasset.author.url_id != '6p0000000000000014':
            asset.author = person_for_openid(tpasset.author.profile_page_url,
                tpasset.author.display_name or tpasset.author.preferred_username)
        else:
            asset.author = None

        asset.published = tpasset.published

        if tpasset.object_type == 'Post':
            asset.title = tpasset.title
            asset.summary = tpasset.excerpt
            asset.content = tpasset.rendered_content
            asset.slug = tpasset.filename
        elif tpasset.object_type == 'Comment':
            assert tpasset.text_format == 'html_convert_linebreaks', 'This comment %s has unexpected text formatting %r' % (tpasset.url_id, tpasset.text_format)
            asset.content = tpasset.content.replace('\n', '<br>\n')

            asset.in_reply_to = Asset.objects.get(atom_id=tpasset.in_reply_to.id)
            root_id = tpasset.api_data['root']['id']
            asset.in_thread_of = Asset.objects.get(atom_id=root_id)
        else:
            # what
            logging.error('Unexpected object type %r for asset %s', tpasset.object_type, tpasset.url_id)
            continue

        logging.debug('Hello, %s %s (%s)!', tpasset.object_type.lower(), tpasset.url_id, asset.title)
        asset.save()

        # Everything's public hwhee!


def import_blog(blog_id):
    blog = typepad.Blog.get_by_url_id(blog_id)
    logging.debug('Importing blog %s (%s)', blog_id, blog.title)

    start_index = 1
    while True:
        logging.debug('Fetching posts %d through %d', start_index, start_index+50)
        assets = blog.post_assets.filter(start_index=start_index, max_results=50)
        if not len(assets.entries):
            logging.debug('This page of posts is empty. Done!?')
            break

        import_assets(assets.entries)

        start_index += 50

    start_index = 1
    while True:
        logging.debug('Fetching comments %d through %d', start_index, start_index+50)
        comments = blog.comments.filter(start_index=start_index, max_results=50, published=True)
        if not len(comments.entries):
            logging.debug('This page of comments is empty. Done?!')
            break

        import_assets(comments.entries)

        start_index += 50


if __name__ == '__main__':
    sys.exit(main())
