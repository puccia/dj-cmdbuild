from helpers import ClassFields
from querysets import *

class ActivityFieldsQuerySet(ClassFieldsQuerySet):
    def _filter_by_flow_status(self, tag):
        from django_cmdbuild.models import Lookup
        l = Lookup.objects.get(type='FlowStatus', description=tag)
        return self.filter(flow_status=l.id)
    def completed(self):
        return self._filter_by_flow_status('Completato')
    def started(self):
        return self._filter_by_flow_status('Avviato')
    def stopped(self):
        return self._filter_by_flow_status('Interrotto')

class ActivityFields(ClassFields):
    from django_cmdbuild.models import Lookup
    flow_status = models.IntegerField(db_column='FlowStatus',
        choices=Lookup.objects.choices(u'FlowStatus'))
    priority = models.IntegerField(db_column='Priority', null=True, blank=True)
    activity_definition = models.CharField(max_length=200, db_column='ActivityDefinitionId')
    process_code = models.CharField(max_length=200, db_column='ProcessCode')
    quick_accept = models.BooleanField(db_column='IsQuickAccept')
    activity_description = models.TextField(db_column='ActivityDescription', blank=True)
    objects = QSManager(ActivityFieldsQuerySet)()
