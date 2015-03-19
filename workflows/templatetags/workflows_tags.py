# coding=utf-8

# django imports
from django import template

# workflows imports
from ..utils import get_allowed_transitions, get_state
from workflows import WorkflowBase

register = template.Library()


@register.inclusion_tag('workflows/transitions.html', takes_context=True)
def transitions(context, obj):
    """
    """
    request = context.get("request")
    
    return {
        "transitions": get_allowed_transitions(obj, request.user),
        "state": get_state(obj),
    }

@register.assignment_tag
def allowed_transitions_by_user(obj, user):
    if not isinstance(obj, WorkflowBase):
        raise TypeError('The obj param must be an instance of WorkflowBase')
    return obj.get_allowed_transitions(user)
