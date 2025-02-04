import logging

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from datentool_backend.base import DatentoolModelMixin


class Profile(DatentoolModelMixin, models.Model):
    '''
    adds additional user information
    '''
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                related_name='profile')
    admin_access = models.BooleanField(default=False)
    can_create_process = models.BooleanField(default=False)
    can_edit_basedata = models.BooleanField(default=False)
    settings = models.JSONField(default=dict)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}: {self.user.username}'

    def delete(self, using=None, keep_parents=False, use_protection=False):
        """
        remove profile from all LogHandlers that reference the user
        and remove the handler from all loggers
        before deleting the profile
        """
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]

        for hdlr_ref in list(logging._handlerList):
            hdlr = hdlr_ref()
            if hasattr(hdlr, 'user') and hdlr.user == self:
                del(hdlr.user)
                for logger in loggers:
                    if hdlr in logger.handlers:
                        logger.removeHandler(hdlr)

        # delete user of profile
        user = self.user
        if user:
            user.delete()

        super().delete(using=using,
                       keep_parents=keep_parents,
                       use_protection=use_protection)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    '''auto create profiles for new users'''
    if created:
        Profile(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    '''save profile when user is saved'''
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        pass