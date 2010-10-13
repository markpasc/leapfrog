from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext


class LoginUrl(object):
    def __str__(self):
        try:
            return self.url
        except AttributeError:
            self.url = reverse('signin')
            return self.url


@login_required(login_url=LoginUrl())
def home(request):
    user = request.user

    stream_items = user.stream_items.order_by("-time").select_related()
    stream_items = list(stream_items[:50])

    replies = user.reply_stream_items.filter(root_time__range=(stream_items[-1].time, stream_items[0].time)).select_related()
    reply_by_item = dict()
    for reply in replies:
        item_replies = reply_by_item.setdefault(reply.root_id, set())
        item_replies.add(reply)
    for item in stream_items:
        reply_set = reply_by_item.get(item.obj_id, set())
        item.replies = sorted(iter(reply_set), key=lambda i: i.reply_time)

    data = {
        'stream_items': stream_items,
        'replies': replies,
        'page_title': "%s's neighborhood" % user.person.display_name,
    }

    template = 'rhino/index.jj'
    return render_to_response(template, data,
        context_instance=RequestContext(request))
