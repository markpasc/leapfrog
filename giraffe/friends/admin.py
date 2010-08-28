from django import forms
from django.contrib import admin
from giraffe.friends import models


class PersonAdmin(admin.ModelAdmin):

    list_display = ('display_name', 'user')
    search_fields = ('display_name',)
    filter_horizontal = ('groups',)


class GroupAdmin(admin.ModelAdmin):

    list_display = ('display_name', 'tag')


admin.site.register(models.Person, PersonAdmin)
admin.site.register(models.Group, GroupAdmin)
admin.site.register(models.Identity)
