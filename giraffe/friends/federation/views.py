
import simplejson as json

from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.conf import settings
from django.utils.importlib import import_module
from django.core.urlresolvers import reverse

from giraffe.friends.federation.util import validate_domain, discover_associate_endpoint, verify_association_request


def federation_document(request):
    associate_endpoint = reverse('associate_endpoint')
    dict = {"associate_endpoint":request.build_absolute_uri(associate_endpoint)}
    return HttpResponse(json.dumps(dict), mimetype="application/json")


def associate_endpoint(request):
    if request.method != "POST":
        return HttpResponse("The endpoint expects a POST request", status=405)

    mode = request.POST.get("mode", None)
    if mode is None:
        return HttpResponse("mode is required", status=400)

    domain = request.POST.get("domain", None)
    if domain is not None:
        if not validate_domain(domain):
            return HttpResponse("domain is not valid", status=400)
    else:
        return HttpResponse("domain is required", status=400)

    if mode == "associate":
        return handle_associate(request)
    elif mode == "verify":
        return handle_verify(request)
    else:
        return HttpResponse("unsupported mode", status=400)

    return HttpResponse("foom")


def handle_associate(request):

    if "domain" in request.POST and "verifier" in request.POST:
        domain   = request.POST["domain"]
        verifier = request.POST["verifier"]

        if verify_association_request(domain, verifier):
            engine = import_module(settings.SESSION_ENGINE)
            if engine:
                session = engine.SessionStore(None) # Create a new session
                request.session = session
                session["authenticated_domain"] = domain
                response_body = json.dumps({"token":session.session_key,"expires_in":session.get_expiry_age()})
                return HttpResponse(response_body, mimetype="application/json")
            else:
                return HttpResponse("no association storage backend is available", status=500)
        else:
            return HttpResponse("association request could not be verified", status=409)


# This is a debugging view which will echo back the domain used to request it.
# It should not be enabled on production sites because it may be useful to
# an attacker who has compromised credentials.
def echo_domain(request):
    if request.session:
        if "authenticated_domain" in request.session:
            return HttpResponse(request.session["authenticated_domain"], mimetype="text/plain")
        else:
            return HttpResponse("There is no domain associated with this request's session", status=403)
    else:
        return HttpResponse("no session available", status=500)


def handle_verify(request):
    return HttpResponse("verify?")

