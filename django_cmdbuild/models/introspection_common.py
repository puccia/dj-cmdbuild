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
        cursor.execute('SELECT classname, attributename, classcomment, attributemode, attributedescription, attributelookup, '
               'attributenull, attributedefault '
               'FROM cmdbclasscatalog')
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
                'mode': r['classcomment'],
                'desc': r['attributedescription'],
                'lookup': r['attributelookup'],
                'null': r['attributenull'] == '',
                'default_value': r['attributedefault']
             }

        cursor.execute('SELECT DISTINCT cmdb.classname as class1, cmdb2.classname as class2 FROM cmdbclasscatalog cmdb LEFT JOIN pg_catalog.pg_inherits cat ON cmdb.classid = cat.inhrelid LEFT JOIN cmdbclasscatalog cmdb2 ON cmdb2.classid = cat.inhparent WHERE NOT cmdb2.classname = \'\'')
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

