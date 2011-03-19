from django.contrib import admin

from leapfrog import models


class AccountAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'service', 'ident')
    list_filter = ('service',)
    search_fields = ('display_name', 'ident')
    raw_id_fields = ('person',)

admin.site.register(models.Account, AccountAdmin)


class ObjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'render_mode', 'external_id', 'time')
    list_filter = ('author', 'render_mode', 'service')
    search_fields = ('title', 'author__display_name', 'foreign_id')
    raw_id_fields = ('author', 'image', 'in_reply_to')

    def external_id(self, obj):
        if obj.service and obj.foreign_id:
            return u'%s:%s' % (obj.service, obj.foreign_id)
        if obj.foreign_id:
            return obj.foreign_id
        return None

admin.site.register(models.Object, ObjectAdmin)


class UserStreamAdmin(admin.ModelAdmin):
    list_display = ('obj', 'user', 'time')
    readonly_fields = ('time',)
    raw_id_fields = ('user', 'obj', 'why_account')

admin.site.register(models.UserStream, UserStreamAdmin)


class UserReplyStreamAdmin(admin.ModelAdmin):
    list_display = ('reply', 'root', 'user', 'reply_time')
    raw_id_fields = ('user', 'root', 'reply')

admin.site.register(models.UserReplyStream, UserReplyStreamAdmin)


class PersonAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'permalink_url', 'user')
    list_filter = ('user',)
    search_fields = ('display_name',)
    raw_id_fields = ('user', 'avatar')

admin.site.register(models.Person, PersonAdmin)


admin.site.register(models.Media)
