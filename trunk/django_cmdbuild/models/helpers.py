from django.db import models
from django.utils.translation import ugettext_lazy as _

from expander import ExpanderField

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
        return self._description

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

class QSManager(models.Manager):
    def __init__(self, qs_class):
        super(QSManager, self).__init__()
        self.queryset_class = qs_class
    def get_query_set(self):
        return self.queryset_class(self.model)
    def __getattr__(self, attr, *args):
        try:
            return self.__dict__[attr]
            #return getattr(self.__class__, attr, *args)
        except KeyError:
            return getattr(self.get_query_set(), attr, *args)
     
class ClassFieldsQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(status__exact='A')

    #def get_query_set(self):
    #   return self.active
        
    #def all(self):
    #   print 'all called'
    #   return super(ClassFieldsManager, self).all()

class LookUpManager(QSManager):
    def __init__(self, arg=ClassFieldsQuerySet):
        super(LookUpManager, self).__init__(arg)
    def choices(self, lookup):
        c = self.active().filter(type__exact=lookup).values('id', 'description')
        return [(c['id'], c['description']) for c in c]

class CodeField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 100)
        kwargs.setdefault('db_column', 'Code')
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super(CodeField, self).__init__(*args, **kwargs)

class DescriptionField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 250)
        kwargs.setdefault('db_column', 'Description')
        super(DescriptionField, self).__init__(*args, **kwargs)
    def contribute_to_class(self, cls, name):
        def read_description(self):
            return getattr(self, name)
        setattr(cls, '_description', property(read_description))
        super(DescriptionField, self).contribute_to_class(cls, name)

class IdClassField(models.TextField):
	opts = {'db_column': 'IdClass', 'editable': False}
	def __init__(self):
		pass
	def contribute_to_class(self, cls, name):
		opts = self.opts.copy()
		opts['default'] = '"%s"' % cls._meta.db_table
		super(IdClassField, self).__init__(opts)

class ClassFields:
    id = models.AutoField(primary_key=True, db_column='Id')
    #code = models.CharField(max_length=100, db_column='Code', blank=True, null=True)
    #description = models.CharField(max_length=250, db_column='Description')
    status = models.CharField(max_length=1, db_column='Status', editable=False,
        choices=(('A', _('Active')), ('U', _('Inactive'))))
    user = models.CharField(max_length=20, db_column='User', blank=True, null=True)
    begin_date = models.DateTimeField(db_column='BeginDate', auto_now=True)
    objects = QSManager(ClassFieldsQuerySet)
        


class ActivityFields:
    flowstatus = models.IntegerField(db_column='FlowStatus')
    priority = models.IntegerField(db_column='Priority')
    activitydefinitionid = models.CharField(max_length=200, db_column='ActivityDefinitionId')
    processcode = models.CharField(max_length=200, db_column='ProcessCode')
    isquickaccept = models.BooleanField(db_column='IsQuickAccept')
    activitydescription = models.TextField(db_column='ActivityDescription')

