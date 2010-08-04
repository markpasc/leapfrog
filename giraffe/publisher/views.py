from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from giraffe.publisher.models import Subscription, Asset


def index(request, template=None, content_type=None):
    data = {
        'assets': Asset.objects.all(),
    }

    if template is None:
        template = 'publisher/index.html'
    return render_to_response(template, data,
        context_instance=RequestContext(request), mimetype=content_type)


def asset(request, slug):
    raise NotImplementedError


def subscribe(request):
    if request.method != 'POST':
        return HttpResponse('POST required', status=405, content_type='text/plain')

    try:
        callback = request.GET['hub.callback']
        mode = request.GET['hub.mode']
        topic = request.GET['hub.topic']
    except KeyError, exc:
        return HttpResponse('Parameter %s required' % str(exc), status=400, content_type='text/plain')

    verify = request.GET.getlist('hub.verify')
    if not verify:
        return HttpResponse('Parameter verify required', status=400, content_type='text/plain')

    lease_secs = request.GET.get('hub.lease_seconds')
    secret = request.GET.get('hub.secret')
    verify_token = request.GET.get('hub.verify_token')

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
        return HttpResponse('Unknown mode %r' % mode, status=400, content_type='text/plain')

    if 'async' in verify:
        task.delay(**kwargs)
        return HttpResponse('', status=202, content_type='text/plain')
    elif 'sync' in verify:
        try:
            task(**kwargs)
        except Exception, exc:
            return HttpResponse('%s: %s' % (type(exc).__name__, str(exc)), status=400, content_type='text/plain')
        return HttpResponse('', status=204)

    return HttpResponse("No supported verification modes ('async' and 'sync') in %r" % verify, status=400, content_type='text/plain')
