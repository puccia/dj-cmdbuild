from django.utils.functional import curry

class MaskingDescriptor(object):
    def __init__(self, orig_desc):
        self.orig_desc = orig_desc
    # __get__ must modify the returned manager
    def __get__(self, *args, **kwargs):
        orig_manager = self.orig_desc.__get__(*args, **kwargs)
        class CMDBMapManager(type(orig_manager)):
            def __init__(self, orig):
                for k, v in orig.__dict__.items():
                    self.__dict__[k] = v
            #def _add_items(self, source_col_name, target_col_name, *objs):
            def _DISABLED_add_items(self, source_col_name, target_col_name, *objs):
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

                    # Add the ones that aren't there already
                    sql = ("INSERT INTO %s (\"IdDomain\", \"IdClass1\", \"IdClass2\", \"Status\", %s, %s) "
                        "VALUES ('%s', '\"%s\"', '\"%s\"', 'A', %%s, %%s)" % \
                        (self.join_table, source_col_name, target_col_name, self.join_table,
                        self.instance._meta.db_table, self.model._meta.db_table))
                    for obj_id in (new_ids - existing_ids):
                        cursor.execute(sql,
                            [self._pk_val, obj_id])
                    from django.db import transaction
                    transaction.commit_unless_managed()
        #return CMDBMapManager(orig_manager)
        return orig_manager
            
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
        #setattr(cls, name, MaskingDescriptor(desc))

        from django.db import connection
        cursor = connection.cursor()
        qn = connection.ops.quote_name
        qd = {
            'view': qn(self.db_table),
            'realtable': qn(self.writable_db_table),
            'col': qn(self._get_m2m_column_name(None)),
            'rev': qn(self._get_m2m_reverse_name(None)),
            'insertrule': qn('insertrule_' + self.writable_db_table),
            'deleterule': qn('deleterule_' + self.writable_db_table),
        }
        if not self.reversed:
            qd.update({
                'coltable': qn(cls._meta.db_table),
                'revtable': qn(self.model.to._meta.db_table)
            })
        else:
            qd.update({
                'revtable': qn(cls._meta.db_table),
                'coltable': qn(self.rel.to._meta.db_table)
            })
        cursor.execute('CREATE TEMPORARY VIEW %s AS SELECT * FROM '
            '%s WHERE "Status" = \'A\'' % (qn(self.db_table), qn(self.writable_db_table)))
        insert_rule = 'CREATE RULE %(insertrule)s AS ' \
            'ON INSERT TO %(view)s DO INSTEAD ' \
            'INSERT INTO %(realtable)s ("IdDomain", "IdClass1", "IdClass2", ' \
            '"Status", %(col)s, %(rev)s) VALUES (\'%(realtable)s\', \'%(coltable)s\', ' \
            '\'%(revtable)s\', \'A\', NEW.%(col)s, NEW.%(rev)s)'
        delete_rule = 'CREATE RULE %(deleterule)s AS ' \
            'ON DELETE TO %(view)s DO INSTEAD ' \
            'UPDATE %(realtable)s SET "Status" = \'N\' ' \
            'WHERE %(col)s = OLD.%(col)s AND %(rev)s = OLD.%(rev)s'
        z = insert_rule % qd
        cursor.execute(z)
        z = delete_rule % qd
        cursor.execute(z)
        
    def contribute_to_related_class(self, cls, related):
        super(CMDBManyToManyField, self).contribute_to_related_class(cls, related)
        try:
            name = related.get_accessor_name()
            if name:
                try:
                    desc = cls.__dict__[name]
                    #setattr(cls, name, MaskingDescriptor(desc))
                except KeyError:
                    pass
        except AttributeError:
            pass

