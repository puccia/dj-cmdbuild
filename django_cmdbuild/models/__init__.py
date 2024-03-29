from django.db import models
from django.contrib import admin

from django_cmdbuild.models.querysets import QSManager, ClassFieldsQuerySet

class LookupQuerySet(ClassFieldsQuerySet):
    def type(self, typename):
        "Returns all Lookup objects of the given type."
        return self.active().filter(type__exact=typename)

    def choices(self, typename, value_field='description'):
        """
        Returns all Lookup objects of the given type, in a format
        suitable for usage as the ``choices`` keyword argument to
        a Django field.
        """
        rows = self.type(typename).values('id', value_field)
        return [(r['id'], r[value_field]) for r in rows]

    def get_label(self, typename, label):
        "Returns a single Lookup object w/ the given type and label."
        return self.get(type=typename, description=label)

    def by_label(self, label):
	    return self.get(description=label)

    def get_by_number(self, typename, number):
        "Returns a single Lookup object of the given type and number."
        return self.get(type=typename, number=number)


class Lookup(models.Model):
      objects = QSManager(LookupQuerySet)()
      id = models.IntegerField(primary_key=True, db_column='Id', blank=True, help_text=u'Topic', null=True)
      type = models.CharField(help_text=u'Topic', max_length=32, blank=True, db_column='Type')
      parenttype = models.CharField(help_text=u'Topic', max_length=32, blank=True, db_column='ParentType')
      parentid = models.IntegerField(help_text=u'Topic', blank=True, null=True, db_column='ParentId')
      number = models.IntegerField(help_text=u'Topic', blank=True, null=True, db_column='Number')
      code = models.CharField(help_text=u'Topic', max_length=100, blank=True, db_column='Code')
      description = models.CharField(help_text=u'Topic', max_length=100, blank=True, db_column='Description')
      isdefault = models.NullBooleanField(help_text=u'Topic', blank=True, null=True, db_column='IsDefault')
      status = models.TextField(help_text=u'Topic', blank=True, db_column='Status') # This field type is a guess.
      notes = models.TextField(help_text=u'Topic', blank=True, db_column='Notes')
      class Admin:
          list_display = ('type', 'description')
      class Meta:
          db_table = u'LookUp'
      def __unicode__(self):
          return self.description

class CMDBuildAdmin(admin.ModelAdmin):
    list_display = list_display = ('_description', '_code', 'status')
