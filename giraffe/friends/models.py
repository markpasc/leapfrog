

from django.db import models


class Person(models.Model):

    display_name = models.CharField(max_length=75)
    user = models.OneToOneField('auth.User', null=True, blank=True)
    groups = models.ManyToManyField('Group', related_name="people")

    def __unicode__(self):
        return self.display_name


class Group(models.Model):

    display_name = models.CharField(max_length=75)
    tag = models.CharField(max_length=15, db_index=True, null=True)

    def __unicode__(self):
        return self.display_name

