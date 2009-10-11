# Get version info
from django import settings
try:
    old_version = settings.CMDBUILD_PRE_V1
except AttributeError:
    old_version = False

if old_version:
    catalog_query = 'SELECT classname, attributename, classcomment, ' \
        'attributemode, attributedescription, attributelookup, attributenull, ' \
        'attributedefault FROM cmdbclasscatalog'
    catalog_table_name = 'cmdbclasscatalog'
else:
    catalog_query ='SELECT classname, attributename, attributecomment, ' \
        'attributedescription, attributelookup, attributenotnull, ' \
        'attributedefault FROM system_attributecatalog'
    catalog_table_name = 'system_classcatalog'

class QueryClassCatalog(object):
    """
    Populates a dict representing the structure of the CMDBuild
    database as it appears from the internal catalog itself.
    """
    def __init__(self):
        from django.db import connection
        
        # Initalize the dictionary
        self.classes = {}

        # Retrieve the catalog view's rows from the DB
        cursor = connection.cursor()
        cursor.execute(catalog_query)
        #print cursor.description

        def fetchall(cursor):
            bare_rows = cursor.fetchall()
            for row in bare_rows:
                yield dict(map(lambda seq: (cursor.description[seq[0]][0], seq[1]), 
                    enumerate(row)))

        # We have one row for each field (that is, 0..N rows for each table)
        for r in fetchall(cursor):
            # Make a new dict entry, if we don't have it
            if not r['classname'] in self.classes:
                self.classes[r['classname']] = {}

            self.classes[r['classname']][r['attributename']] = {
                #'mode': r['classcomment'],
                'desc': r['attributedescription'],
                'lookup': r['attributelookup'],
                #'null': r['attributenull'] == '',
                'default_value': r['attributedefault']
            }

            if old_version:
                self.classes[r['classname']][r['attributename']]['null'] = (
                    r['attributenull'] == '' )
            else:
                self.classes[r['classname']][r['attributename']]['null'] = (
                    not r['attributenotnull'])

        cursor.execute('SELECT DISTINCT cmdb.classname as class1, '
            'cmdb2.classname as class2 FROM ' + catalog_table_name + ' cmdb '
            'LEFT JOIN pg_catalog.pg_inherits cat '
            'ON cmdb.classid = cat.inhrelid '
            'LEFT JOIN ' + catalog_table_name + ' cmdb2 '
            'ON cmdb2.classid = cat.inhparent '
            'WHERE NOT cmdb2.classname = \'\'')
        rows= cursor.fetchall()
        for r in rows:
            if r[0] not in self.classes:
                self.classes[r[0]] = {}
            if 'class_parents' not in self.classes[r[0]]:
                self.classes[r[0]]['class_parents'] = []
            self.classes[r[0]]['class_parents'].append(r[1])


    def __call__(self, cls, attr):
        return self.classes[cls][attr]

query_class_catalog = QueryClassCatalog()

