from django.db import models

from django_cmdbuild.models.querysets import QSManager, ClassFieldsQuerySet

class LookUpManager(QSManager(ClassFieldsQuerySet)):
    def choices(self, lookup):
        c = self.active().filter(type__exact=lookup).values('id', 'description')
        return [(c['id'], c['description']) for c in c]


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
