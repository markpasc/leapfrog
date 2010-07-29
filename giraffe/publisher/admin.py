from django.contrib import admin

from giraffe.publisher.models import Asset, Subscription


class AssetAdmin(admin.ModelAdmin):

    prepopulated_fields = {'slug': ('title',)}


admin.site.register(Asset, AssetAdmin)
admin.site.register(Subscription)
