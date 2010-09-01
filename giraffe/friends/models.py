from django.db import models
from django.dispatch import Signal


merge_person = Signal(providing_args=('person', 'into_person'))


class Person(models.Model):

    display_name = models.CharField(max_length=75)
    user = models.OneToOneField('auth.User', null=True, blank=True)
    groups = models.ManyToManyField('Group', related_name='_people', blank=True)
    userpic_url = models.CharField(max_length=300, blank=True)
    profile_url = models.CharField(max_length=300, blank=True)

    def __unicode__(self):
        return self.display_name

    def merge_into(self, into_person):
        for group in self.groups.all():
            into_person.groups.add(group)

        Identity.objects.filter(person=self).update(person=into_person)

        # Let others do whatever they need too.
        merge_person.send(Person, person=self, into_person=into_person)


class Group(models.Model):

    display_name = models.CharField(max_length=75)
    tag = models.CharField(max_length=300, db_index=True, null=True)
    people = models.ManyToManyField(Person, through=Person.groups.through,
        related_name='_groups', blank=True)

    def __unicode__(self):
        return self.display_name


class Identity(models.Model):

    person = models.ForeignKey(Person)
    openid = models.CharField(max_length=300, unique=True)

    def __unicode__(self):
        return self.openid
