# coding=utf-8
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import ugettext_lazy as _

from models import WorkflowBase, State
from utils import get_wf_dict_value


def create_transition_method(transition_name, transition_condition=''):
    def transition_method(self, user, comment=None):
        transition = transition_name.lower()
        checker_name = "check_%s" % transition.replace(' ', '_')
        # default conditional method
        checker = getattr(self, checker_name, None)
        # specific conditional method
        condition_method = getattr(self, transition_condition, None)

        checked = (not checker or checker(user) is True) and (not condition_method or condition_method(user) is True)

        return self.do_transition(transition_name, user, comment) if checked else checked
    return transition_method


def create_state_method(state_name):
    def state_method(self):
        try:
            state = State.objects.get(name=state_name, workflow=self.get_workflow())
        except State.DoesNotExist:
            return False
        return self.get_state() == state
    return state_method


def create_manager_state_method(state_name):
    def manager_state_method(self):
        queryset_method = getattr(self.get_queryset(), state_name.lower(), None)
        return queryset_method() if queryset_method else self.get_queryset()
    return manager_state_method


def create_queryset_state_method(state_name):
    def queryset_state_method(self):
        return self.filter(current_state__name=state_name)
    return queryset_state_method


def create_manager_get_queryset_method(manager, queryset_mixin):
    def manager_get_queryset_method(self):
        queryset_class = manager.get_queryset().__class__

        class ExtendedQuerySet(queryset_mixin, queryset_class):
            pass

        return ExtendedQuerySet(self.model, using=self._db)
    return manager_get_queryset_method


def workflow_enabled(cls):

    if models.Model not in cls.__mro__:
        raise ImproperlyConfigured(_('The decorator "workflow_enabled" only is applied to subclasses of Django Model'))

    bases = list(cls.__bases__)
    if not WorkflowBase in bases:
        bases.insert(0, WorkflowBase)
        cls.__bases__ = tuple(bases)

        current_state = models.ForeignKey(State, verbose_name=_(u"State"), name='current_state', null=True, blank=True)
        current_state.contribute_to_class(cls=cls, name='current_state')


    workflows_settings = getattr(settings, 'WORKFLOWS', {})
    wf_item = workflows_settings.get("%s.%s" % (cls.__module__, cls.__name__), None)

    try:
        wf_name = wf_item['name']
    except KeyError:
        raise ImproperlyConfigured('The attribute or key (name), must be specified in the workflow configuration.')

    # building transition methods
    transitions = get_wf_dict_value(wf_item, 'transitions', wf_name)
    for transition in transitions:
        name = get_wf_dict_value(transition, 'name', wf_name, 'transitions')
        condition = transition.get('condition', '')
        # building method name
        method_name = "do_%s" % name.lower().replace(' ', '_')
        # building method
        cls_transition_method = getattr(cls, method_name, None)
        if not cls_transition_method:
            setattr(cls, method_name, create_transition_method(name, condition))

    class CustomQuerySetMixin(object):
        pass

    class CustomManagerMixin(object):

        def get_queryset(self):
            return CustomQuerySetMixin(self.model, using=self._db)

    cls._default_manager = CustomManagerMixin()

    # building state methods
    initial_state = get_wf_dict_value(wf_item, 'initial_state', wf_name)
    initial_state_name = get_wf_dict_value(initial_state, 'name', wf_name, 'initial_state')
    # building instance method
    instance_method_name = "is_%s" % initial_state_name.lower().replace(' ', '_')
    cls_instance_method = getattr(cls, instance_method_name, None)
    if not cls_instance_method:
        setattr(cls, instance_method_name, property(create_state_method(initial_state_name)))

    # building manager method
    manager_method_name = "%s" % initial_state_name.lower().replace(' ', '_')
    cls_manager_method = getattr(CustomManagerMixin, manager_method_name, None)
    if not cls_manager_method:
        setattr(CustomManagerMixin, manager_method_name, create_manager_state_method(initial_state_name))
    cls_queryset_method = getattr(CustomQuerySetMixin, manager_method_name, None)
    if not cls_queryset_method:
        setattr(CustomQuerySetMixin, manager_method_name, create_queryset_state_method(initial_state_name))

    states = get_wf_dict_value(wf_item, 'states', wf_name)
    for state in states:
        state_name = get_wf_dict_value(state, 'name', wf_name, 'states')
        # building method
        method_name = "is_%s" % state_name.lower().replace(' ', '_')
        cls_state_method = getattr(cls, method_name, None)
        if not cls_state_method:
            setattr(cls, method_name, property(create_state_method(state_name)))

        # building manager method
        manager_method_name = "%s" % state_name.lower().replace(' ', '_')
        cls_manager_method = getattr(CustomManagerMixin, manager_method_name, None)
        if not cls_manager_method:
            setattr(CustomManagerMixin, manager_method_name, create_manager_state_method(state_name))
        cls_queryset_method = getattr(CustomQuerySetMixin, manager_method_name, None)
        if not cls_queryset_method:
            setattr(CustomQuerySetMixin, manager_method_name, create_queryset_state_method(state_name))

    # extending manager
    cls._meta.concrete_managers.sort()
    managers = [(mgr_name, manager) for order, mgr_name, manager in cls._meta.concrete_managers]
    setattr(cls, '_default_manager', None)  # clean the default manager
    setattr(cls._meta, 'concrete_managers', [])  # clean the managers
    for mgr_name, manager in managers:
        class ExtendedManager(CustomManagerMixin, manager.__class__):
            pass

        setattr(ExtendedManager, 'get_queryset', create_manager_get_queryset_method(manager, CustomQuerySetMixin))
        cls.add_to_class(mgr_name, ExtendedManager())

    return cls