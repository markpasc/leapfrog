from django.contrib import admin

from giraffe.publisher.models import Asset, Subscription


class AssetAdmin(admin.ModelAdmin):

    list_display = ('title', 'slug', 'preview')
    prepopulated_fields = {'slug': ('title',)}


admin.site.register(Asset, AssetAdmin)
admin.site.register(Subscription)
