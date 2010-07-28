from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from giraffe.admin import amend_admin
from giraffe.profile.models import ProfileInfo
from giraffe.profile.forms import ProfileForm


class ProfileInfoAdmin(admin.ModelAdmin):

    list_display = ('user', 'field', 'label')
    change_list_template = 'butt.html'

    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['form'] = ProfileForm()
        return super(ProfileInfoAdmin, self).changelist_view(request, extra_context)


admin.site.register(ProfileInfo, ProfileInfoAdmin)
