from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_cmdbuild.remoteapi import http

from expander import ExpanderField
from querysets import *

def from_kwargs(func):
    def wrapper(*args, **kwargs):
        name, value = kwargs.items()[0]
        del kwargs[name]
        kwargs['name'] = name
        kwargs['value'] = value
        return func(*args, **kwargs)
    return wrapper

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

    @classmethod
    def _make_bean(cls, name, value):
        """
        Take an attribute name and value (for this class), and return an
        AssetBean that can be serialized and provided to CMDBuild over
        a remote API call.
        """
        from django_cmdbuild.serializer.jsonconverter import as_string, AssetBean
        # If it is an object, use its ID
        if isinstance(value, models.Model):
            value = value.pk
        return AssetBean(name=cls._meta.get_field(name).db_column,
            value=as_string(value))

    @classmethod
    def _get_cmdbuild_attributemap(cls, attributes):
        """
        Take a dictionary of attribute/value pairs and turn the Django instance
        attribute names into CMDBuild attribute names.
        """
        if isinstance(value, models.Model):
            value = value.pk
        return dict([(cls._meta.get_field(name).db_column, value) for name, value
            in attributes.items()])


class CMDBActivityOptions(CMDBModelOptions):

    class ReadOnly(Exception):
        """
        NEVER save an Activity instance directly -- it would get out
        of sync with respect to the Shark workflow.
        """
        pass

    def save(self):
        "Ban any attempt to save the instance."
        raise self.ReadOnly, 'Cannot save an Activity class'

    def _get_history(self):
        """
        Return a QuerySet with all cards belonging to this flow instance.
        """
        return self.__class__.objects.with_inactive().filter(
            process_code=self.process_code).order_by('begin_date')
    history = property(_get_history)

    def _get_flow_begin_date(self):
        """
        Return this flow's begin date.
        """
        return self.history[0].begin_date
    flow_begin_date = property(_get_flow_begin_date)

    def _get_flow_status_code(self):
        return Lookup.objects.get(type='FlowStatus',id=self.flow_status)

    def _is_stopped(self):
        return self.flow_status == Lookup.objects.get(type='FlowStatus', code='Interrotto')
    stopped = property(_is_stopped)
    
    def _is_started(self):
        return self.flow_status == Lookup.objects.get(type='FlowStatus', code='Avviato')
    started = property(_is_started)
        
    def _is_completed(self):
        return self.flow_status == Lookup.objects.get(type='FlowStatus', code='Completato')
    completed = property(_is_completed)

    @from_kwargs
    def update_attribute(self, name, value):
        """
        Update an attribute of this class (with ``attname=value`` syntax).
        TODO: make sure that the Python instance is updated or discarded,
        as its own attributes keep their old values.
        """
        remote = http.Remote()
        resp = remote.request('card.update.id',( self._meta.db_table, self.pk,
            self._make_bean(name, value)))
        if resp is not True:
            raise remote.GenericApplicationException(req)

    @classmethod
    def create(cls, **kwargs):
        """
        Ask CMDBuild to start a new instance of this Activity.  If any
        attributes are provided, set them.
        """
        remote = http.Remote()
        table = cls._meta.db_table
        resp = remote.request('workflow.process.start', [table,
            cls._get_cmdbuild_attributemap(kwargs)])
        return cls.objects.get(process_code=resp)

    def advance(self, **kwargs):
	    """
	    Ask CMDBuild to let this activity step ahead, optionally updating
	    its attributes.
	    """
	    remote = http.Remote()
	    table = self._meta.db_table
	    return remote.request('workflow.process.update', [table,
	        self.id, self._get_cmdbuild_attributemap(kwargs)])

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
    def _filter_by_flow_status(self, tag):
        from django_cmdbuild.models import Lookup
        l = Lookup.objects.get(type='FlowStatus', description=tag)
        return self.filter(flow_status=l.id)
    def completed(self):
        return self._filter_by_flow_status('Completato')
    def started(self):
        return self._filter_by_flow_status('Avviato')
    def stopped(self):
        return self._filter_by_flow_status('Interrotto')

class ActivityFields(ClassFields):
    from django_cmdbuild.models import Lookup
    flow_status = models.IntegerField(db_column='FlowStatus',
        choices=Lookup.objects.choices(u'FlowStatus'))
    priority = models.IntegerField(db_column='Priority', null=True, blank=True)
    activity_definition = models.CharField(max_length=200, db_column='ActivityDefinitionId')
    process_code = models.CharField(max_length=200, db_column='ProcessCode')
    quick_accept = models.BooleanField(db_column='IsQuickAccept')
    activity_description = models.TextField(db_column='ActivityDescription', blank=True)
    objects = QSManager(ActivityFieldsQuerySet)()