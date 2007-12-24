from django.db import models

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
            
            
        

class ClassFieldsManager(models.Manager):
    def _get_active(self, *args, **kwargs):
        return models.Manager.get_query_set(self).filter(status__exact='A')
    active = property(_get_active)

    def get_query_set(self):
		return self.active
		
	#def all(self):
	#	print 'all called'
	#	return super(ClassFieldsManager, self).all()

class LookUpManager(ClassFieldsManager):
    def choices(self, lookup):
        c = self.active.filter(type__exact=lookup).values('id', 'description')
        return [(c['id'], c['description']) for c in c]


class ClassFields:
    id = models.AutoField(primary_key=True, db_column='Id')
    code = models.CharField(max_length=100, db_column='Code', blank=True, null=True)
    description = models.CharField(max_length=250, db_column='Description')
    status = models.CharField(max_length=1, db_column='Status', editable=False)
    user = models.CharField(max_length=20, db_column='User', blank=True, null=True)
    begindate = models.DateTimeField(db_column='BeginDate', auto_now=True)
    objects = ClassFieldsManager()

class ActivityFields:
    flowstatus = models.IntegerField(db_column='FlowStatus')
    priority = models.IntegerField(db_column='Priority')
    activitydefinitionid = models.CharField(max_length=200, db_column='ActivityDefinitionId')
    processcode = models.CharField(max_length=200, db_column='ProcessCode')
    isquickaccept = models.BooleanField(db_column='IsQuickAccept')
    activitydescription = models.TextField(db_column='ActivityDescription')

