from django.contrib.auth.models import User
from django.db import models


class ProfileInfo(models.Model):

    field = models.CharField(max_length=100, help_text="The kind of profile information this is")
    label = models.CharField(max_length=100, blank=True, help_text="Which of the user's infos of this kind this is")
    value = models.CharField(max_length=100)
