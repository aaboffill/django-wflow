# coding=utf-8
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import ugettext_lazy as _
from workflows import WorkflowBase, State, get_or_create_workflow


def create_transition_method(transition):
    def transition_method(self, user, comment=None):
        transition_name = transition.name.lower()
        checker_name = "check_%s" % transition_name.replace(' ', '_')
        # default conditional method
        checker = getattr(self, checker_name, None)
        # specific conditional method
        condition_method = getattr(self, transition.condition, None)

        checked = (not checker or checker() is True) and (not condition_method or condition_method() is True)

        return self.do_transition(transition, user, comment) if checked else checked
    return transition_method


def create_state_method(state):
    def state_method(self):
        return self.get_state() == state
    return state_method


def workflow_enabled(cls, workflow=None):

    if models.Model not in cls.__mro__:
        raise ImproperlyConfigured(_('The decorator "workflow_enabled" only is applied to subclasses of Django Model'))

    workflow = workflow or get_or_create_workflow(cls)

    if workflow:
        bases = list(cls.__bases__)
        if not WorkflowBase in bases:
            bases.insert(0, WorkflowBase)
            cls.__bases__ = tuple(bases)

        # building transition methods
        transitions = workflow.transitions.all()
        for transition in transitions:
            # building method name
            transition_name = transition.name.lower()
            method_name = "do_%s" % transition_name.replace(' ', '_')

            # building method
            cls_transition_method = getattr(cls, method_name, None)
            if not cls_transition_method:
                setattr(cls, method_name, create_transition_method(transition))

        # building state methods
        states = workflow.states.all()
        for state in states:
            # building method name
            state_name = state.name.lower()
            method_name = "is_%s" % state_name.replace(' ', '_')

            # building method
            cls_state_method = getattr(cls, method_name, None)
            if not cls_state_method:
                setattr(cls, method_name, property(create_state_method(state)))

        current_state = models.ForeignKey(State, verbose_name=_(u"State"), name='current_state', null=True, blank=True)
        current_state.contribute_to_class(cls=cls, name='current_state')

    return cls