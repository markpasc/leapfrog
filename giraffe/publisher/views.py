from functools import wraps
import logging

from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
try:
    from django.views.decorators.csrf import csrf_exempt
except ImportError:
    from django.contrib.csrf.middleware import csrf_exempt

from giraffe.publisher.models import Subscription, Asset
from giraffe.publisher import tasks


def index(request, template=None, content_type=None):
    data = {
        # TODO: get the assets that the user is allowed to see
        'assets': Asset.objects.all().filter(private_to=None).order_by('-published')[:10],
    }

    if template is None:
        template = 'publisher/index.html'
    return render_to_response(template, data,
        context_instance=RequestContext(request), mimetype=content_type)


def asset(request, slug, template=None):
    try:
        asset = Asset.objects.get(slug=slug)
    except Asset.DoesNotExist:
        raise Http404

    # TODO: let users who are allowed to see the asset see it
    if asset.private_to.count():
        raise Http404

    data = {
        'asset': asset,
    }

    if template is None:
        template = 'publisher/asset.html'
    return render_to_response(template, data,
        context_instance=RequestContext(request))


def oops(func):
    @wraps(func)
    def otherfunc(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception, exc:
            logging.exception(exc)
            raise
    return otherfunc


@csrf_exempt
@oops
def subscribe(request):
    log = logging.getLogger("%s.subscribe" % __name__)
    if request.method != 'POST':
        return HttpResponse('POST required', status=405, content_type='text/plain')

    try:
        callback = request.POST['hub.callback']
        mode = request.POST['hub.mode']
        topic = request.POST['hub.topic']
    except KeyError, exc:
        log.debug("Parameter %s required", str(exc))
        return HttpResponse('Parameter %s required' % str(exc), status=400, content_type='text/plain')

    verify = request.POST.getlist('hub.verify')
    if not verify:
        log.debug("Parameter verify required")
        return HttpResponse('Parameter verify required', status=400, content_type='text/plain')

    lease_secs = request.POST.get('hub.lease_seconds')
    secret = request.POST.get('hub.secret')
    verify_token = request.POST.get('hub.verify_token')

    try:
        sub = Subscription.objects.get(callback=callback)
    except Subscription.DoesNotExist:
        if mode == 'unsubscribe':
            # Already gone!
            return HttpResponse('', status=204)
        sub = Subscription(callback=callback)

    kwargs = {
        'callback': callback,
        'mode': mode,
        'topic': topic,
        'lease_seconds': lease_secs,
        'secret': secret,
        'verify_token': verify_token,
    }

    if mode not in ('subscribe', 'unsubscribe'):
        log.debug("Unknown mode %r", mode)
        return HttpResponse('Unknown mode %r' % mode, status=400, content_type='text/plain')

    task = tasks.verify_subscription

    if 'async' in verify:
        task.delay(**kwargs)
        return HttpResponse('', status=202, content_type='text/plain')
    elif 'sync' in verify:
        try:
            task(**kwargs)
        except Exception, exc:
            log.debug("%s: %s", type(exc).__name__, str(exc))
            return HttpResponse('%s: %s' % (type(exc).__name__, str(exc)), status=400, content_type='text/plain')
        return HttpResponse('', status=204)

    log.debug("This should not have happened")
    return HttpResponse("No supported verification modes ('async' and 'sync') in %r" % verify, status=400, content_type='text/plain')
