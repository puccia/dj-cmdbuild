from django.core.management.base import NoArgsCommand, CommandError

def log(string):
    print '# %s' % string

class Field(object):
    def __init__(self, name, klass=None, param=None):
        self.name = name
        self.kw_params = {}
        if param:
            self.params = [param]
        else:
            self.params = []
        self.comments = []
        if klass:
            self.set_class(klass)
        self.mangle_name()
    def add_kw_param(self, name, value, representation=True):
        if representation:
            value = '%r' % value
        self.kw_params[name] = value
    def add_param(self, value, representation=True):
        if representation:
            value = '%r' % value
        self.params.append(value)
    def add_comment(self, comment):
        self.comments.append(comment)
    def set_class(self, klass):
        self.klass = klass
    def line(self):
        if hasattr(self, 'db_column'):
            self.add_kw_param('db_column', self.db_column)
        params = self.params + ['%s=%s' % (k, v) for k, v in self.kw_params.items()] 
        l = '    %s = %s(%s)' % (self.name, self.klass, ', '.join(params))
        if self.comments:
            l += ' # ' + ' '.join(self.comments)
        yield l
    def mangle_name(self):
        if ' ' in self.name:
            self.name = att_name.replace(' ', '')
            self.add_comment('Field renamed to remove spaces.')
        import keyword
        if keyword.iskeyword(self.name):
            self.name += '_field'
            self.add_comment('Field renamed because it was a Python reserved word.')
        
        pass
    def set_column(self, column_name):
        self.db_column = column_name
            
class Vertex(object):
    def __init__(self, name, graph=None):
        self.name = name
        self.store = graph
        self.edge_out = {}
        self.edge_in = {}
    def add_edge(self, name):
        if name not in self.edge_out:
            self.edge_out[name] = 1
            self.store.vertex(name).edge_in[self.name] = 1
    def remove_edge(self, name):
        del self.edge_out[name]
        del self.store.vertex(name).edge_in[self.name]
    def has_outgoing_edges(self):
        return len(self.edge_out.keys()) > 0
    def has_incoming_edges(self):
        return len(self.edge_in.keys()) > 0

table2model = lambda table_name: table_name.title().replace('_', '')

class ModelClass(Vertex):
    def __init__(self, name, store=None, graph=None):
        Vertex.__init__(self, name, graph=graph)
        self.base_classes = ['models.Model']
        self.lines = []
        self.extra_attributes = []
        self.fields = []
        self.name = name
        self.store = store
    def add_base_class(self, name):
        self.base_classes.append(name)
    def add(self, line):
        self.lines.append(line)
    def extra(self, line):
        self.add('      %s' % line)
    def add_field(self, field):
        self.fields.append(field)
    def yield_self(self):
        if not len(self.lines):
            return
        yield 'class %s(%s):' % (table2model(self.name), ', '.join(self.base_classes))
        for f in self.fields:
            for l in f.line():
                yield l
        yield '      class Admin:'
        if 'ClassFields' in self.base_classes:
            yield "          list_display = ('description', 'code', 'status')"
        else:
            yield "          pass"
        for l in self.lines:
            yield l
        raise StopIteration
        
class ModelStore(object):
    def __init__(self):
        self.models = {}
        self.bases = {}
    def vertex(self, name):
        return self.model(name)
    def model(self, name):
        try:
            return self.models[name]
        except KeyError:
            self.models[name] = ModelClass(name, store=self)
            return self.models[name]
    def delete(self, name):
        del(self.models[name])
    def with_classfields(self):
        self.bases['Class'] = 1
        self.bases['ExpanderField'] = 1
    def with_activityfields(self):
        self.bases['Activity'] = 1
        self.bases['ExpanderField'] = 1
    def with_lookup(self):
        self.bases['LookUp'] = 1
    def with_mapfields(self):
        self.bases['MapFields'] = 1
    def with_manytomany(self):
        self.bases['CMDBManyToManyField'] = 1
    def sorted_models(self):
        q = filter(lambda x: not x.has_incoming_edges(), self.models.values())
        l = []
        while len(q) > 0:
            model = q.pop()
            log('Processing %s' % model.name)
            l.append(model)
            for needed in model.edge_out.keys():
                log( ' %s depends on %s, removing' % (model.name, needed))
                model.remove_edge(needed)
                if not self.model(needed).has_incoming_edges():
                    log('  %s has nothing else depending on it, queueing' % needed)
                    q.append(self.model(needed))
                else:
                    log('  %s still has %s depending on it' % (needed, self.model(needed).edge_in.keys()))
        if len(filter(lambda x: x.has_incoming_edges(), self.models.values())) > 0:
            for m in self.models.values():
                if m.has_incoming_edges():
                    m.extra('# Caught in a cycle!')
                    l.append(m)
        for b in self.bases.keys():
            if b == 'Class':
                yield 'from django_cmdbuild.models.helpers import ClassFieldsManager, ClassFields'
            elif b == 'Activity':
                yield 'from django_cmdbuild.models.helpers import ActivityFields'
            elif b == 'LookUp':
                yield "from django_cmdbuild.models.helpers import LookUpManager"
            elif b == 'CMDBManyToManyField':
                yield "from django_cmdbuild.models.related import %s" % b
            elif b == 'ExpanderField':
                yield "from django_cmdbuild.models.expander import %s" % b
            else:
                yield "from django_cmdbuild.models.helpers import %s" % b
        for m in l:
            yield m

from django_cmdbuild.models.introspection_common import query_class_catalog

class Command(NoArgsCommand):
    help = "Introspects the database tables in the given database and outputs a Django model module."

    requires_model_validation = False

    def handle_noargs(self, **options):
        try:
            for line in self.handle_inspection():
                print line
        except NotImplementedError:
            raise CommandError("Database inspection isn't supported for the currently selected database backend.")
    
    
    def output_classfields(self):
        yield 'AAA'
        if not getattr(self, 'classfields_are_out'):
            print 'BBB'
            yield ''
            self.classfields_are_out = True

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self._dom_cache = None

    def query_dom_catalog(self, name):
        if self._dom_cache is None:
            self._dom_cache = {}
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute('SELECT domainname, domainclass1, domainclass2, domaincardinality '
                'FROM cmdbdomaincatalog')
            for row in cursor.fetchall():
                self._dom_cache[row[0]] = {'name': row[0], 'class1': row[1],
                    'class2': row[2], 'cardinality': row[3]}
        try:
            return self._dom_cache[name]
        except IndexError:
            raise KeyError('No catalog entry for table %s' % name)
    
    def handle_inspection(self):
        from django.db import connection, get_introspection_module
        import keyword

        introspection_module = get_introspection_module()

        def maptable2attr(name):
            name = name.lower()
            if name.startswith('map_'):
                name = name[4:]
            return name + 's'

        cursor = connection.cursor()
        yield "# This is an auto-generated Django model module."
        yield "# You'll have to do the following manually to clean this up:"
        yield "#     * Rearrange models' order"
        yield "#     * Make sure each model has one field with primary_key=True"
        yield "# Feel free to rename the models, but don't rename db_table values or field names."
        yield "#"
        yield "# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'"
        yield "# into your database."
        yield ''
        yield 'from django.db.models import *'
        yield 'from django.db import models'
        yield ''
        
        store = ModelStore()
        
        for table_name in introspection_module.get_table_list(cursor):
            # Internal "service" views
            if table_name.startswith('cmdb') and table_name.endswith('catalog'):
                continue
            if table_name in ('relationhistorylist', 'relationlist'):
                continue 
            # History views are handled separately
            if table_name.endswith('_history'):
                continue
            # LookUp has its own built-in model
            if table_name == 'LookUp':
                continue
            mc = store.model(table_name)
            # Special CMDBuild cases
            skip_rows = []
            extra_attributes = []
            names = []
            # Collect
            for row in introspection_module.get_table_description(cursor, table_name):
                names.append(row[0].lower())
            def subset(small, big):
                bools= map(lambda x: x in big, small)
                excluder = filter(lambda y: y != True, bools)
                return len(excluder) == 0

            activity_relations = ('flowstatus', 'priority',
                'activitydefinitionid', 'processcode', 'isquickaccept',
                'activitydescription')
            class_relations = ('id', 'code', 'description', 'status',
                'user', 'begindate', 'idclass')
            
            if subset(class_relations, names):
                skip_rows.extend(class_relations)
                if subset(activity_relations, names):
                    skip_rows.extend(activity_relations)
                    mc.add_base_class('ActivityFields')
                    mc.add_base_class('CMDBActivityOptions')
                    mc.extra('activityfields = ExpanderField(ActivityFields)')
                    store.with_activityfields()
                else:
                    mc.add_base_class('ClassFields')
                    mc.add_base_class('CMDBModelOptions')
                    mc.extra('commonfields = ExpanderField(ClassFields)')
                    store.with_classfields()
                

            map_relations = ('iddomain', 'idclass1', 'idclass2', 'status',
                'user', 'begindate', 'enddate')

            if subset(map_relations, names):
                try:
                    cat_info = self.query_dom_catalog(mc.name)
                    if cat_info['cardinality'] == 'N:N':
                        store.with_manytomany()
                        first_table = store.model(cat_info['class1'])
                        first_table.extra('%s = CMDBManyToManyField(%s, db_table=\'%s\', blank=True, null=True)' % (
                            maptable2attr(table_name),
                            cat_info['class2'],
                            table_name))
                        store.model(cat_info['class2']).add_edge(first_table.name)
                        store.delete(mc.name)
                        continue
                    else:
                        mc.extra('# Links %s and %s with cardinality %s' %( cat_info['class1'],
                            cat_info['class2'], cat_info['cardinality']))
                        mc.extra('# Foreign keys should be available in the objects')
                except KeyError:
                    log('%s not found' % mc.name)
                    pass
                skip_rows.extend(map_relations)
                mc.add_base_class('MapFields')
                mc.extra('mapfields = ExpanderField(MapFields)')
                store.with_mapfields()

            try:
                relations = introspection_module.get_relations(cursor, table_name)
            except NotImplementedError:
                relations = {}
            try:
                indexes = introspection_module.get_indexes(cursor, table_name)
            except NotImplementedError:
                indexes = {}
            
            log('%s: %s' % (table_name, indexes))
            try:
                log ('inheritance: %s %s' % (table_name, query_class_catalog(table_name, 'class_parents')))
            except KeyError:
                pass
            
            for i, row in enumerate(introspection_module.get_table_description(cursor, table_name)):
                log('%s' % (row,))
                att_name = row[0].lower()
                if att_name in skip_rows:
                    continue
                f = Field(att_name)
                comment_notes = [] # Holds Field notes, to be displayed in a Python comment.
                extra_params = {}  # Holds Field parameters such as 'db_column'.
                try:
                    cat_entry = query_class_catalog(mc.name, row[0])
                except KeyError:
                    #cat_entry = None
                    log('%s, %s not found' % (mc.name, row[0]))
                    
                f.set_column(row[0])
                # extra_params['db_column'] = '%r' % column_name
                # Special treatment for idclass
                #if f.name == 'idclass':
                #    f.name = '_' + f.name
                #    f.add_kw_param('editable', False)
                #    f.add_kw_param('default', '"%s"' % table_name)
                if f.name == 'code':
                    f.set_class('CodeField')
                elif f.name == 'description':
                    f.set_class('DescriptionField')
                elif i in relations:
                    #mc.add_edge(relations[i][1])
                    store.model(relations[i][1]).add_edge(mc.name)
                    rel_to = relations[i][1] == table_name and "'self'" or table2model(relations[i][1])
                    #field_type = 'ForeignKey(%s' % rel_to
                    f.set_class('models.ForeignKey')
                    f.add_param(rel_to, representation=False)
                    if f.name.endswith('_id'):
                        f.name = f.name[:-3]
                else:
                    try:
                        field_type = introspection_module.DATA_TYPES_REVERSE[row[1]] 
                    except KeyError:
                        field_type = 'TextField'
                        f.add_comment('This field type is a guess.')
                    f.set_class('models.' + field_type)


                    # This is a hook for DATA_TYPES_REVERSE to return a tuple of
                    # (field_type, extra_params_dict).
                    if type(field_type) is tuple:
                        field_type, new_params = field_type
                        for k, v in new_params.items():
                            f.add_kw_param(k, v)
                        extra_params.update(new_params)

                    # Add max_length for all CharFields.
                    if field_type == 'CharField' and row[3]:
                        f.add_kw_param('max_length', row[3])

                    if field_type == 'DecimalField':
                        f.add_kw_param('max_digits', row[4])
                        f.add_kw_param('decimal_places', row[5])
                        #extra_params['max_digits'] = '%r' % row[4]
                        #extra_params['decimal_places'] = '%r' % row[5]
                    
                    if cat_entry:
                        # Add help text.
                        if cat_entry['desc']:
                            f.add_kw_param('help_text', cat_entry['desc'])
                            #extra_params['help_text'] = '%r' % cat_entry['desc']
                        if ( len(cat_entry['lookup']) > 0 
                            and (not table_name == 'Lookup')):
                            #extra_params['choices'] = 'Lookup.objects.choices(%r)' % cat_entry['lookup']
                            #f.add_kw_param('choices', 'Lookup.objects.choices(%r)' % cat_entry['lookup'],
                                #representation=False)
                            #store.model('LookUp').add_edge(mc.name)
                            f.set_class('LookupField')
                            f.add_param(cat_entry['lookup'])
                            #store.with_lookup()

                    # Add primary_key and unique, if necessary.
                    if f.db_column in indexes:
                        if indexes[f.db_column]['primary_key']:
                            #extra_params['primary_key'] = 'True'
                            f.add_kw_param('primary_key', True)
                        elif indexes[f.db_column]['unique']:
                            #extra_params['unique'] = 'True'
                            f.add_kw_param('unique', True)

                    field_type += '('

                # Don't output 'id = meta.AutoField(primary_key=True)', because
                # that's assumed if it doesn't exist.
                if att_name == 'id' and field_type == 'AutoField(' and extra_params == {'primary_key': True}:
                    continue

                # Add 'null' and 'blank', if the 'null_ok' flag was present in the
                # table description.
                try:
                    if cat_entry['null']: # If it's NULL...
                        f.add_kw_param('blank', True)
                        if not field_type in ('TextField(', 'CharField('):
                            f.add_kw_param('null', True)
                except TypeError:
                    pass

                #field_desc = '%s = models.%s' % (att_name, field_type)
                #if extra_params:
                #    if not field_desc.endswith('('):
                #        field_desc += ', '
                #    field_desc += ', '.join(['%s=%s' % (k, v) for k, v in extra_params.items()])
                #field_desc += ')'
                #if comment_notes:
                    #field_desc += ' # ' + ' '.join(comment_notes)
                #mc.add( '      %s' % field_desc)
                mc.add_field(f)
            mc.add( '      class Meta:')
            mc.add( '          db_table = %r' % table_name)
            mc.add( '')
            #for l in mc.yield_self():
            #   yield l
        log(store.models)
        for m in store.sorted_models():
            if isinstance(m, str):
                yield m
            else:
                for l in m.yield_self():
                    yield l

def inspect():
    Command().handle_noargs()
            
if __name__ == '__main__':
    inspect()
