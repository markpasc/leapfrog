from django.contrib import admin

from rhino import models


class AccountAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'service', 'ident')

admin.site.register(models.Account, AccountAdmin)


class ObjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'render_mode', 'external_id')

    def external_id(self, obj):
        if not obj.service or not obj.foreign_id:
            return None
        return u'%s:%s' % (obj.service, obj.foreign_id)

admin.site.register(models.Object, ObjectAdmin)


class UserStreamAdmin(admin.ModelAdmin):
    list_display = ('obj', 'user', 'time')
    readonly_fields = ('time',)

admin.site.register(models.UserStream, UserStreamAdmin)


class UserReplyStreamAdmin(admin.ModelAdmin):
    list_display = ('reply', 'root', 'user', 'reply_time')

admin.site.register(models.UserReplyStream, UserReplyStreamAdmin)


admin.site.register(models.Person)
admin.site.register(models.Media)
