from django.db import models

from django_cmdbuild.models.querysets import QSManager, ClassFieldsQuerySet

class LookUpManager(QSManager(ClassFieldsQuerySet)):
    def type(self, typename):
		"Returns all Lookup objects of the given type."
	    return self.active().filter(type__exact=typename)

    def choices(self, typename):
		"""
		Returns all Lookup objects of the given type, in a format
		suitable for usage as the ``choices`` keyword argument to
		a Django field.
		"""
        rows = self.type(typename).values('id', 'description')
        return [(r['id'], r['description']) for r in rows]

    def get_label(self, typename, label):
		"Returns a single Lookup object w/ the given type and label."
		return self.get(type=typename, description=label)


class Lookup(models.Model):
	  objects = LookUpManager()
	  id = models.IntegerField(primary_key=True, db_column='Id', blank=True, help_text=u'Topic', null=True)
	  type = models.CharField(help_text=u'Topic', max_length=32, blank=True, db_column='Type')
	  parenttype = models.CharField(help_text=u'Topic', max_length=32, blank=True, db_column='ParentType')
	  parentid = models.IntegerField(help_text=u'Topic', blank=True, null=True, db_column='ParentId')
	  number = models.IntegerField(help_text=u'Topic', blank=True, null=True, db_column='Number')
	  code = models.CharField(help_text=u'Topic', max_length=100, blank=True, db_column='Code')
	  description = models.CharField(help_text=u'Topic', max_length=100, blank=True, db_column='Description')
	  isdefault = models.BooleanField(help_text=u'Topic', blank=True, null=True, db_column='IsDefault')
	  status = models.TextField(help_text=u'Topic', blank=True, db_column='Status') # This field type is a guess.
	  notes = models.TextField(help_text=u'Topic', blank=True, db_column='Notes')
	  class Admin:
		  pass
	  class Meta:
		  db_table = u'LookUp'
