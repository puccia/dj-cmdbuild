from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_cmdbuild.models.expander import ExpanderField
from django_cmdbuild.models.querysets import *
from django_cmdbuild.models import Lookup

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
        """
        Saves a CMDbuild instance, taking care to set the ``status`` flag
        and to get the right default value by polling the DB.
        """
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
    
    
    
    def delete(self):
        from django.utils.encoding import smart_unicode
        pk_val = self._get_pk_val()
        pk_set = pk_val is not None and smart_unicode(pk_val) != u''
        assert pk_set, "%s object can't be deleted because its %s attribute" \
            " is set to None." % (self._meta.object_name, self._meta.pk.attname)
        self.status = 'N'
        self.save()

    def __unicode__(self):
        try:
            if self._description:
                return self._description
        except AttributeError:
            pass
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
        # Turn objects into ids and turn names into column names
        _map = {}
        for name, value in attributes.items():
            if isinstance(value, models.Model):
                value = value.pk
            _map[cls._meta.get_field(name).db_column] = value
        return _map

    def _get_full_attributemap(self):
        """
        Returns all attributes in a map. Mostly useful for debugging.
        """
        return dict([(f.attname, getattr(self, f.attname))
            for f in self._meta.fields])

    def _reload(self):
        """
        Gets the instance again from the DB and copies the field
        attributes.  Ugly, but works.
        """
        updated = self.__class__.objects.get(pk=self.pk)
        for field in self._meta.fields:
            key = field.attname
            setattr(self, key, getattr(updated, key))

class CodeField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 100)
        kwargs.setdefault('db_column', 'Code')
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super(CodeField, self).__init__(*args, **kwargs)
    def get_internal_type(self):
        return "CharField"
    def contribute_to_class(self, cls, name):
        def read_code(self):
            return getattr(self, name)
        setattr(cls, '_code', property(read_code))
        super(CodeField, self).contribute_to_class(cls, name)

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

class LookupDescriptor(object):
	def __init__(self, attribute_name):
		self.attribute_name = attribute_name
	

class LookupField(models.IntegerField):
	def get_internal_type(self):
		return "IntegerField"
	def __init__(self, lookup_type, *args, **kwargs):
		self.lookup_type = lookup_type
		kwargs.setdefault('choices', Lookup.objects.choices(lookup_type))
		super(LookupField, self).__init__(*args, **kwargs)
	def get_lookup_obj(self, number):
		return Lookup.objects.get_by_number(self.lookup_type, number)
	def get_lookup_label(self, number):
		return self.get_lookup_obj(number).description
	def contribute_to_class(self, cls, name):
		self.attribute_name = name
		super(LookupField, self).contribute_to_class(cls, name)
		setattr(cls, name + '_text', property(lambda instance:
			self.get_lookup_label(getattr(instance, name))))
		setattr(cls, name + '_objects', Lookup.objects.filter(
			type=self.lookup_type))
	def get_db_prep_save(self, value):
		if isinstance(value, Lookup):
			if value.type != self.lookup_type:
				# TODO: Subclass Exception
				raise Exception, 'Saving wrong lookup type'
			value = value.number
		return super(LookupField, self).get_db_prep_save(value)

class IdClassField(models.TextField):
    ### XXX Check that this makes sense
    rel = None
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
    notes = models.TextField(_('notes'), db_column='Notes', blank=True, null=True)
        
