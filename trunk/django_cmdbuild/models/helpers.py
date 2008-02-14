from django.db import models
from django.utils.translation import ugettext_lazy as _

from expander import ExpanderField

from querysets import *

class MapFields:
    pass

class CMDBModelOptions(object):
    def save(self, *args, **kwargs):
        if hasattr(self, 'status'):
            self.status = 'A'
        if self._meta.has_auto_field:
            from django.utils.encoding import smart_unicode
            pk_val = self._get_pk_val()
            pk_set = pk_val is not None and smart_unicode(pk_val) != u''
            if not pk_set:
                from django.db import connection
                from introspection_common import query_class_catalog
                cursor = connection.cursor()
                sql = 'SELECT ' + query_class_catalog(self._meta.db_table, self._meta.pk.db_column)['default_value']
                cursor.execute(sql)
                r = cursor.fetchall()[0]
                setattr(self, self._meta.pk.attname, r[0])
        models.Model.save(self, *args, **kwargs)

    def __unicode__(self):
        if self._description:
            return self._description
        else:
            return unicode(self.pk)
   

    def _get_status_and_date(self):
        if self.status == 'A':
            r = _(u'Active (%s)')  % self.begin_date
            return r
        elif self.status == 'U':
            return _(u'Inactive (%s-%s)') % (
                self.begin_date, self.end_date)
        else:
            return self.status
    status_and_date = property(_get_status_and_date)

    def _get_end_date(self):
        """
        For an inactive instance, returns the timestamp of its closing.
        """
        # Check that we are not active
        if self.status == 'A':
            return None

        # Create the class on the fly; change the table; set the attribute
        class history_model(CMDBModelOptions, models.Model, ClassFields):
            _enddate = models.DateTimeField(db_column='EndDate', editable=False)
            commonfields = ExpanderField(ClassFields)
            class Meta:
                db_table = self._meta.db_table + '_history'

        # Set the manager
        #history_model.objects.contribute_to_class(history_model, objects)

        # Retrieve the instance
        instance = history_model.objects.get(pk=self.pk)

        return instance._enddate
    end_date = property(fget=_get_end_date)

class CMDBActivityOptions(CMDBModelOptions):
    class ReadOnly(Exception):
        pass
    def save(self):
        raise self.ReadOnly, 'Cannot save an Activity class'

class CodeField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 100)
        kwargs.setdefault('db_column', 'Code')
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super(CodeField, self).__init__(*args, **kwargs)
    def get_internal_type(self):
        return "CharField"

class DescriptionField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 250)
        kwargs.setdefault('db_column', 'Description')
        super(DescriptionField, self).__init__(*args, **kwargs)
    def get_internal_type(self):
        return "CharField"
    def contribute_to_class(self, cls, name):
        def read_description(self):
            return getattr(self, name)
        setattr(cls, '_description', property(read_description))
        super(DescriptionField, self).contribute_to_class(cls, name)

class IdClassField(models.TextField):
    def __init__(self):
        pass
    opts = {'db_column': 'IdClass', 'editable': False}
    def contribute_to_class(self, cls, name):
        opts = self.opts.copy()
        opts['default'] = '"%s"' % cls._meta.db_table
        super(IdClassField, self).__init__(**opts)
        super(IdClassField, self).contribute_to_class(cls, name)
    def get_internal_type(self):
        return "TextField"

class ClassFields:
    id = models.AutoField(primary_key=True, db_column='Id')
    idclass = IdClassField()
    #code = models.CharField(max_length=100, db_column='Code', blank=True, null=True)
    #description = models.CharField(max_length=250, db_column='Description')
    status = models.CharField(max_length=1, db_column='Status', editable=False,
        choices=(('A', _('Active')), ('U', _('Inactive'))))
    user = models.CharField(max_length=20, db_column='User', blank=True, null=True)
    begin_date = models.DateTimeField(db_column='BeginDate', auto_now=True)
    objects = QSManager(ClassFieldsQuerySet)()
	    

class ActivityFieldsQuerySet(ClassFieldsQuerySet):
	def filter_by_flowstatus(self, tag):
		from django_cmdbuild.models import Lookup
		l = Lookup.objects.get(type='FlowStatus', description=tag)
		return self.filter(flowstatus=l.id)
	def completed(self):
		return self.filter_by_flowstatus('Completato')

class ActivityFields(ClassFields):
    from django_cmdbuild.models import Lookup
    flowstatus = models.(db_column='FlowStatus',
        choices=Lookup.objects.choices(u'FlowStatus'))
    priority = models.IntegerField(db_column='Priority', null=True, blank=True)
    activitydefinitionid = models.CharField(max_length=200, db_column='ActivityDefinitionId')
    processcode = models.CharField(max_length=200, db_column='ProcessCode')
    isquickaccept = models.BooleanField(db_column='IsQuickAccept')
    activitydescription = models.TextField(db_column='ActivityDescription', blank=True)
    objects = QSManager(ActivityFieldsQuerySet)()
