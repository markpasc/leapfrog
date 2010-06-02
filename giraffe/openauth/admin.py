from django.conf.urls.defaults import url, patterns
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from giraffe.openauth.models import UserOpenID


class OpenIDInline(admin.TabularInline):

    model = UserOpenID
    extra = 0


class GiraffeUserAdmin(UserAdmin):

    inlines = [OpenIDInline]

    def import_friends(self, request):
        # Find this user's openids.
        # Find those openids' friends.
        # Find which of those friend openids don't already exist.
        # Provide a form for associating those with users and groups.
        raise NotImplementedError

    def get_urls(self):
        urls = super(GiraffeUserAdmin, self).get_urls()
        extra_urls = patterns('',
            url(r'^import_friends/$', self.admin_site.admin_view(self.import_friends), name='admin_import_friends'),
        )
        return extra_urls + urls  # me first


class UserOpenIDAdmin(admin.ModelAdmin):

    list_display = ('openid', 'user_name')

    def user_name(self, obj):
        user = obj.user
        return user.get_full_name() or user.username


admin.site.unregister(User)
admin.site.register(User, GiraffeUserAdmin)

admin.site.register(UserOpenID, UserOpenIDAdmin)
