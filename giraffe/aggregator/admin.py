from django.contrib import admin

from giraffe.aggregator import models


admin.site.register(models.Subscription)
admin.site.register(models.Activity)
admin.site.register(models.Object)
