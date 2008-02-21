from django_cmdbuild.models.helpers import ClassFields, CMDBModelOptions, LookupField
from django_cmdbuild.models.querysets import *
from django_cmdbuild.remoteapi import http

class CMDBActivityOptions(CMDBModelOptions):

    class ReadOnly(Exception):
        """
        NEVER save an Activity instance directly -- it would get out
        of sync with respect to the Shark workflow.
        """
        pass

    def save(self):
        "Ban any attempt to save the instance."
        raise self.ReadOnly, 'Cannot save an Activity class'

    def _get_history(self):
        """
        Return a QuerySet with all cards belonging to this flow instance.
        """
        return self.__class__.objects.with_inactive().filter(
            process_code=self.process_code).order_by('begin_date')
    history = property(_get_history)

    def _get_flow_begin_date(self):
        """
        Return this flow's begin date.
        """
        return self.history[0].begin_date
    flow_begin_date = property(_get_flow_begin_date)

    def _get_flow_status_code(self):
        return Lookup.objects.get(type='FlowStatus',id=self.flow_status)

    def _is_stopped(self):
        return self.flow_status == Lookup.objects.get(type='FlowStatus', code='Interrotto')
    stopped = property(_is_stopped)
    
    def _is_started(self):
        return self.flow_status == Lookup.objects.get(type='FlowStatus', code='Avviato')
    started = property(_is_started)
        
    def _is_completed(self):
        return self.flow_status == Lookup.objects.get(type='FlowStatus', code='Completato')
    completed = property(_is_completed)

    def update_attribute(self, **attrmap):
        """
        Update an attribute of this class (with ``attname=value`` syntax).
        """
        remote = http.Remote()
        args = [self._meta.db_table, self.pk] + [self._make_bean(k, v)
            for k, v in attrmap.items()]
        resp = remote.request('card.update.id', args)
        if resp is not True:
            raise remote.GenericApplicationException(req)
        self._reload()

    @classmethod
    def create(cls, **kwargs):
        """
        Ask CMDBuild to start a new instance of this Activity.  If any
        attributes are provided, set them.
        """
        remote = http.Remote()
        table = cls._meta.db_table
        resp = remote.request('workflow.process.start', [table,
            cls._get_cmdbuild_attributemap(kwargs)])
        return cls.objects.get(process_code=resp)

    def advance(self, **kwargs):
        """
        Ask CMDBuild to let this activity step ahead, optionally updating
        its attributes.
        """
        remote = http.Remote()
        table = self._meta.db_table
        reply = remote.request('workflow.process.update',
            [self._meta.db_table, self.pk,
            self._get_cmdbuild_attributemap(kwargs)])
        self._reload()
        return reply


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

class ActivityManager(QSManager(ActivityFieldsQuerySet)):
    def create(self, **kwargs):
        """
        Ask CMDBuild to start a new instance of this Activity.  If any
        attributes are provided, set them.
        """
        remote = http.Remote()
        table = self.model._meta.db_table
        resp = remote.request('workflow.process.start', [table,
            self.model._get_cmdbuild_attributemap(kwargs)])
        return self.model.objects.get(process_code=resp)

class ActivityFields(ClassFields):
    from django_cmdbuild.models import Lookup
    flow_status = LookupField('FlowStatus', db_column='FlowStatus')
    priority = models.IntegerField(db_column='Priority', null=True, blank=True)
    activity_definition = models.CharField(max_length=200, db_column='ActivityDefinitionId')
    process_code = models.CharField(max_length=200, db_column='ProcessCode')
    quick_accept = models.BooleanField(db_column='IsQuickAccept')
    activity_description = models.TextField(db_column='ActivityDescription', blank=True)
    objects = ActivityManager()

