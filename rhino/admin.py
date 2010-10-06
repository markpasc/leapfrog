from django.contrib import admin

from rhino import models


admin.site.register(models.Account)
admin.site.register(models.Object)
admin.site.register(models.UserStream)
admin.site.register(models.UserReplyStream)
