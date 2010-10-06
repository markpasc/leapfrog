from django.contrib import admin

from rhino import models


admin.site.register(models.Subscription)
admin.site.register(models.Object)
admin.site.register(models.UserStream)
