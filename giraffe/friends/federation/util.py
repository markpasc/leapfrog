
import urllib2
import simplejson as json
import re


def validate_domain(domain):
    if re.match("^[a-z0-9-]+(\.[a-z0-9-]+)+$", domain):
        return True
    else:
        return False


def discover_associate_endpoint(domain):
    doc = fetch_federation_document(domain)
    if "associate_endpoint" in doc:
        return doc["associate_endpoint"]
    else:
        return None


def verify_association_request(domain, verifier):
    return True


def fetch_federation_document(domain):
    url = "http://%s/.well-known/federation" % domain
    try:
        f = urllib2.urlopen(url)
    except urllib2.URLError:
        return {}

    try:
        return json.load(f)
    except ValueError:
        return {}


def make_verifier(domain):
    from django.conf import settings
    import hashlib
    secret = settings.SECRET_KEY
    return hashlib.sha256("\n".join((domain, secret))).hexdigest()


