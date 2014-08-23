from django.db import models
from django.utils.translation import ugettext_lazy as _


class BrightcoveItems(models.Model):
    """
    This class is storing the brightcove fields and managing the generic relationship
    """
    brightcove_id = models.BigIntegerField(verbose_name=_('Brightcove id'), primary_key=True)
    name = models.CharField(verbose_name=_('Name'), max_length=255, null=True, blank=True)
    video_still_URL = models.CharField(verbose_name=_('Video still url'), max_length=255, null=True, blank=True)
    thumbnail_URL = models.CharField(verbose_name=_('Thumbnail url'), max_length=255, null=True, blank=True)
    short_description = models.TextField(verbose_name=_('Short description'), null=True, blank=True)
    long_description = models.TextField(verbose_name=_('Short description'), null=True, blank=True)
    length = models.IntegerField(verbose_name=_('Length'), null=True, blank=True)
    link_URL = models.CharField(verbose_name=_('Link url'), max_length=255, null=True, blank=True)
    plays_total = models.PositiveIntegerField(verbose_name=_('Number of plays'), null=True, blank=True)
    creation_date = models.DateTimeField(verbose_name=_('Creation date'), null=True, blank=True)
    published_date = models.DateTimeField(verbose_name=_('Published date'), null=True, blank=True)

    def __unicode__(self):
        if self.name:
            return self.name
        return self.brightcove_id

    @property
    def length_seconds(self):
        return float(self.length/1000)

    @property
    def long_description_normalized(self):
        return self._normalize(self.long_description)

    @property
    def short_description_normalized(self):
        return self._normalize(self.short_description)

    @property
    def plays_total_normalized(self):
        return self._normalize(self.plays_total)

    @property
    def _normalize(self, arg):
        if arg is None:
            if isinstance(arg, basestring):
                return ''
            else:
                return 0
        return arg