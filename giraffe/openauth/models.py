from django.db import models


class UserOpenID(models.Model):

    user = models.ForeignKey('auth.User')
    openid = models.CharField(max_length=200, unique=True, verbose_name='OpenID')

    def __unicode__(self):
        return self.openid

    def __repr__(self):
        return '<UserOpenID %s for %s>' % (self.openid, self.user.username)

    class Meta:
        verbose_name = 'user OpenID'
        verbose_name_plural = 'user OpenIDs'
