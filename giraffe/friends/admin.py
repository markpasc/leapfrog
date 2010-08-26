from django.contrib import admin
from giraffe.friends import models


admin.site.register(models.Person)
admin.site.register(models.Group)
admin.site.register(models.Identity)
