from django.contrib import admin

from giraffe.publisher.models import Asset, Subscription


class AssetAdmin(admin.ModelAdmin):

    list_display = ('title', 'author', 'slug', 'preview')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'slug', 'summary', 'content')
    filter_horizontal = ('private_to',)


admin.site.register(Asset, AssetAdmin)
admin.site.register(Subscription)
