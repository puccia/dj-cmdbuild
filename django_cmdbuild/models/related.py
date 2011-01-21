from django.utils.functional import curry

# Get version info
from django.conf import settings
try:
    old_version = settings.CMDBUILD_PRE_V1
except AttributeError:
    old_version = False

class MaskingDescriptor(object):
    def __init__(self, orig_desc, querydict):
        self.orig_desc = orig_desc
        self.querydict = querydict
    # __get__ must modify the returned manager
    def __get__(self_desc, *args, **kwargs):
        orig_manager = self_desc.orig_desc.__get__(*args, **kwargs)
        class CMDBMapManager(type(orig_manager)):
            def __init__(self, orig):
                for k, v in orig.__dict__.items():
                    self.__dict__[k] = v
            #def _add_items(self, source_col_name, target_col_name, *objs):
            def _add_items(self, source_col_name, target_col_name, *objs):
                # join_table: name of the m2m link table
                # source_col_name: the PK colname in join_table for the source object
                # target_col_name: the PK colname in join_table for the target object
                # *objs - objects to add. Either object instances, or primary keys of object instances.

                # If there aren't any objects, there is nothing to do.
                if objs:
                    # Check that all the objects are of the right type
                    new_ids = set()
                    for obj in objs:
                        if isinstance(obj, self.model):
                            new_ids.add(obj._get_pk_val())
                        else:
                            new_ids.add(obj)
                    # Add the newly created or already existing objects to the join table.
                    # First find out which items are already added, to avoid adding them twice
                    from django.db import connection
                    cursor = connection.cursor()
                    cursor.execute("SELECT %s FROM %s WHERE %s = %%s AND %s IN (%s)" % \
                        (target_col_name, self.join_table, source_col_name,
                        target_col_name, ",".join(['%s'] * len(new_ids))),
                        [self._pk_val] + list(new_ids))
                    existing_ids = set([row[0] for row in cursor.fetchall()])

                    # Get IDs
                    if source_col_name == '"IdObj1"':
                        invert = False
                    elif source_col_name == '"IdObj2"':
                        invert = True
                    else:
                        raise Exception, 'Invalid column name: %s' % source_col_name
                    cursor.execute ("""
                    SELECT '"%(realtable)s"'::regclass::integer,
                        '"%(coltable)s"'::regclass::integer,
                        '"%(revtable)s"'::regclass::integer
                    """ % self_desc.querydict)
                    relation_oid, col_oid, rev_oid = cursor.fetchall()[0]
                    idclass1_oid, idclass2_oid = col_oid, rev_oid
                    
                    sql = """SELECT createrelation('%(domainid)s', '%(idclass1)s',
                        '%(idobj1)s', '%(idclass2)s', '%(idobj2)s', 'A', 'dj-cmdbuild',
                        '%(realtable)s')
                    """ % {
                        'domainid': relation_oid,
                        'idclass1': idclass1_oid,
                        'idobj1': '%s',
                        'idclass2': idclass2_oid,
                        'idobj2': '%s',
                        'realtable': self_desc.querydict['realtable'],
                    }
                    if not invert:
                        for obj_id in (new_ids - existing_ids):
                            cursor.execute(sql,
                                [self._pk_val, obj_id])
                    else:
                        for obj_id in (new_ids - existing_ids):
                            cursor.execute(sql,
                                [obj_id, self._pk_val])                        
                    from django.db import transaction
                    transaction.commit_unless_managed()
        return CMDBMapManager(orig_manager)
        #return orig_manager
            
from django.db import models

class CMDBManyToManyField(models.ManyToManyField):
    def __init__(self, *args, **kwargs):
        kwargs['limit_choices_to'] = {'status__exact': 'A'}
        self.reversed = False
        if 'reversed' in kwargs:
            if kwargs['reversed']:
                self.reversed = True
                del kwargs['reversed']
        # Create a temporary view to handle SELECTs
        self.writable_db_table = kwargs['db_table']
        kwargs['db_table'] = 'pure_' + kwargs['db_table']
        super(CMDBManyToManyField, self).__init__(*args, **kwargs)
        qd = {
            'view': self.db_table,
            'realtable': self.writable_db_table,
            'col': self._get_m2m_column_name(None),
            'rev': self._get_m2m_reverse_name(None),
            'deleterule': 'deleterule_' + self.writable_db_table,
            'reversed': self.reversed
        }
        self.querydict = qd
        
    def _get_m2m_column_name(self, related):
        if self.reversed:
            return 'IdObj2'
        else:
            return 'IdObj1'
    def _get_m2m_reverse_name(self, related):
        if self.reversed:
            return 'IdObj1'
        else:
            return 'IdObj2'
    def _get_m2m_db_readonly_view(self, opts):
        return 'pure_' + self._get_m2m_db_table(opts)
    def contribute_to_class(self, cls, name):
        super(CMDBManyToManyField, self).contribute_to_class(cls, name)
        desc = cls.__dict__[name]
        setattr(cls, name, MaskingDescriptor(desc, self.querydict))

        if not self.reversed:
            self.querydict.update({
                'coltable': cls._meta.db_table,
                'revtable': self.model.to._meta.db_table,
            })
        else:
            self.querydict.update({
                'revtable': cls._meta.db_table,
                'coltable': self.rel.to._meta.db_table,
            })


        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('CREATE OR REPLACE TEMPORARY VIEW "%s" AS SELECT * FROM '
            '"%s" WHERE "Status" = \'A\'' % (self.db_table, self.writable_db_table))
                        
        delete_rule = 'CREATE OR REPLACE RULE "%(deleterule)s" AS ' \
            'ON DELETE TO "%(view)s" DO INSTEAD ' \
            'UPDATE "%(realtable)s" SET "Status" = \'N\' ' \
            'WHERE "%(col)s" = OLD."%(col)s" AND "%(rev)s" = OLD."%(rev)s"'
        cursor.execute(delete_rule % self.querydict)
        
    def contribute_to_related_class(self, cls, related):
        super(CMDBManyToManyField, self).contribute_to_related_class(cls, related)
        try:
            name = related.get_accessor_name()
            if name:
                try:
                    desc = cls.__dict__[name]
                    setattr(cls, name, MaskingDescriptor(desc, self.querydict))
                except KeyError:
                    pass
        except AttributeError:
            pass
    
        