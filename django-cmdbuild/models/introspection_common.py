class QueryClassCatalog(object):
    def __init__(self):
        from django.db import connection
        self.classes = {}
        cursor = connection.cursor()
        cursor.execute('SELECT classname, attributename, classcomment, attributemode, attributedescription, attributelookup, '
               'attributenull = \'\', attributedefault '
               'FROM cmdbclasscatalog')
        rows = cursor.fetchall()
        for r in rows:
            if not r[0] in self.classes:
                self.classes[r[0]] = {}
            self.classes[r[0]][r[1]] = {'mode': r[3], 'desc': r[4], 'lookup': r[5], 'null': r[6], 'default_value': r[7]}
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

