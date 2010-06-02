from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from giraffe.openauth.models import UserOpenID


class OpenIDInline(admin.TabularInline):

    model = UserOpenID
    extra = 0


class GiraffeUserAdmin(UserAdmin):

    inlines = [OpenIDInline]


class UserOpenIDAdmin(admin.ModelAdmin):

    list_display = ('openid', 'user_name')

    def user_name(self, obj):
        user = obj.user
        return user.get_full_name() or user.username


admin.site.unregister(User)
admin.site.register(User, GiraffeUserAdmin)

admin.site.register(UserOpenID, UserOpenIDAdmin)
