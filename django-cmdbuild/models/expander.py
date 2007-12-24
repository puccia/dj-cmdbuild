import types
from copy import deepcopy
from django.db import models

class ExpanderField(object):
    """
    This type of field can be used to include some common fields and methods in models.
    It take a class with those common things as parameter in the constructor and will 
    add all fields in that class to models classes in which a field of
    this class type is declared. If the class containing common fields 
    have fields of type: ForeignKey and ManyToManyField, then the related_name attribute
    of those fields will be renamed to a value of the form: model_name_original_value .
    Ej: if related_name = child_set and model name is MenuItem, it will be renamed to 
    MenuItem_child_set. To add methods of the common class you must inherit from it.
    An importan thing to note here is that you must inherit first from the common class, 
    order matters.

    Use case:
    class ContentManager(models.Manager):
        pass
        
    class CommonFields:
        pub_date = models.DateTimeField()
        created_by = models.ForeignKey(User, related_name = 'created_by_set')
        last_modified_by = models.ForeignKey(User, related_name = 'last_modified_by_set')

        objects = ContentManager()

        def save(self):
            #do something
            pass
            
    class NewsItem(CommonFields, models.Model):
        title = models.CharField(maxlength = 100)
        body = models.CharField(maxlength = 200)
        common = ExpanderField(CommonFields)

    this will create a class of this form:

    class NewsItem(models.Model):
        title = models.CharField(maxlength = 100)
        body = models.CharField(maxlength = 200)
        pub_date = models.DateTimeField()
        created_by = models.ForeignKey(User, related_name = 'created_by_set')
        last_modified_by = models.ForeignKey(User, related_name = 'last_modified_by_set')

        objects = ContentManager()

    """
    def __init__(self, field_container_class):
        self.field_container_class = field_container_class

    def contribute_to_class(self, cls, name):
        attr_list = [attr for attr in dir(self.field_container_class) 
                     if attr not in  ('__doc__', '__module__', '__class__', '__dict__')]
        container = self.field_container_class
        
        for attr in attr_list:
            clone = None
            attr_value = getattr(container, attr)
            
            if type(attr_value) != types.MethodType:
                clone = deepcopy(attr_value)
                
                if (isinstance(clone, models.ForeignKey) or 
                    isinstance(clone, models.ManyToManyField)) and \
                    clone.rel.related_name is not None:
                    clone.rel.related_name = cls.__name__ + '_' + clone.rel.related_name
                
            if clone is not None:
                cls.add_to_class(attr, clone)
