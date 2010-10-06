from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from rhino.models import *


#@login_required
def home(request):
    data = {}

    # TEMP HACK: For now, default to user 1 until we have working login
    user = request.user if request.user else User.objects.get(id=1)

    stream_items = user.stream_items.all().filter(user=user).order_by("-time")

    tmpl_stream_items = []
    data["stream_items"] = tmpl_stream_items

    for item in stream_items:
        tmpl_item = {}
        tmpl_stream_items.append(tmpl_item)
        tmpl_item["main_object"] = item.obj

    template = 'rhino/index.jj'
    return render_to_response(template, data,
        context_instance=RequestContext(request))
