from django.db import models

def QSManager(the_queryset_class):
    class QSManagerType(models.Manager):
        queryset_class = the_queryset_class
        def __init__(self, active_only=True):
            super(QSManagerType, self).__init__()
            self.active_only = active_only
        def get_query_set(self):
            qs = self.__class__.queryset_class(self.model)
            if self.active_only:
                qs = qs.active()
            return qs
        def all(self):
            return self.get_query_set()
        def with_inactive(self):
            # Warning: this does not chain! TODO: document this clearly
            return self.__class__.queryset_class(self.model)
        def __getattr__(self, attr, *args):
            try:
                return super(QSManagerType, self).__getattr__(attr, *args)
            except AttributeError:
                if 'model' in self.__dict__:
                    return getattr(self.__class__.get_query_set(self), attr, *args)
                else:
                    raise 
    QSManagerType.__name__ = the_queryset_class.__name__ + 'Manager'
    return QSManagerType

class ClassFieldsQuerySet(models.query.QuerySet):
    def active(self):
        return self.filter(status__exact='A')

