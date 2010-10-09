from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render_to_response
from django.template import RequestContext


#@login_required
def home(request):
    data = {}

    # TEMP HACK: For now, default to user 1 until we have working login
    user = request.user if request.user else User.objects.get(id=1)

    stream_items = user.stream_items.order_by("-time").select_related()
    stream_items = list(stream_items[:50])

    replies = user.reply_stream_items.filter(root_time__range=(stream_items[-1].time, stream_items[0].time)).select_related()

    data = {
        'stream_items': stream_items,
        'replies': replies,
        'page_title': "%s's neighborhood" % user.person.display_name,
    }

    template = 'rhino/index.jj'
    return render_to_response(template, data,
        context_instance=RequestContext(request))
