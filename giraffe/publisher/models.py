from django.contrib.auth.models import User
from django.db import models


class Asset(models.Model):

    title = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    content = models.TextField(blank=True)
    slug = models.SlugField()


class Subscription(models.Model):

    callback = models.CharField(max_length=200)
    secret = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(User, blank=True, null=True)
    lease_until = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
