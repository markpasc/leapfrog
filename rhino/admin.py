from django.contrib import admin

from rhino import models


class AccountAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'service', 'ident')

admin.site.register(models.Person)
admin.site.register(models.Account, AccountAdmin)
admin.site.register(models.Object)
admin.site.register(models.Media)
admin.site.register(models.UserStream)
admin.site.register(models.UserReplyStream)
