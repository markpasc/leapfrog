from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext


@login_required
def home(request):
    data = {}

    template = 'rhino/index.jj'
    return render_to_response(template, data,
        context_instance=RequestContext(request))
