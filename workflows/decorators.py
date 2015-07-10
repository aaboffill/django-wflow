# coding=utf-8
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import ugettext_lazy as _
from workflows import WorkflowBase, State, get_or_create_workflow, get_wf_dict_value


def create_transition_method(transition_name, transition_condition=''):
    def transition_method(self, user, comment=None):
        transition = transition_name.lower()
        checker_name = "check_%s" % transition.replace(' ', '_')
        # default conditional method
        checker = getattr(self, checker_name, None)
        # specific conditional method
        condition_method = getattr(self, transition_condition, None)

        checked = (not checker or checker() is True) and (not condition_method or condition_method() is True)

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


def workflow_enabled(cls):

    if models.Model not in cls.__mro__:
        raise ImproperlyConfigured(_('The decorator "workflow_enabled" only is applied to subclasses of Django Model'))

    bases = list(cls.__bases__)
    if not WorkflowBase in bases:
        bases.insert(0, WorkflowBase)
        cls.__bases__ = tuple(bases)

    current_state = models.ForeignKey(State, verbose_name=_(u"State"), name='current_state', null=True, blank=True)
    current_state.contribute_to_class(cls=cls, name='current_state')

    get_or_create_workflow(cls)

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

    # building state methods
    initial_state = get_wf_dict_value(wf_item, 'initial_state', wf_name)
    initial_state_name = get_wf_dict_value(initial_state, 'name', wf_name, 'initial_state')
    method_name = "is_%s" % initial_state_name.lower().replace(' ', '_')
    # building method
    cls_state_method = getattr(cls, method_name, None)
    if not cls_state_method:
        setattr(cls, method_name, property(create_state_method(initial_state_name)))

    states = get_wf_dict_value(wf_item, 'states', wf_name)
    for state in states:
        state_name = get_wf_dict_value(state, 'name', wf_name, 'states')
        method_name = "is_%s" % state_name.lower().replace(' ', '_')
        # building method
        cls_state_method = getattr(cls, method_name, None)
        if not cls_state_method:
            setattr(cls, method_name, property(create_state_method(state_name)))

    return cls