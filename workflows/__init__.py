# coding=utf-8
import inspect
from settings import *
from collections import Iterable

# django imports
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.contrib.auth.models import User, Group
from django.db.models.base import Model

# permissions imports
from permissions.utils import add_local_role

# workflows imports
import utils
# workflow imports
from workflows.models import WorkflowHistorical


class WorkflowBase(object):
    """Mixin class to make objects workflow aware.
    """

    def get_workflow(self):
        """Returns the current workflow of the object.
        """
        # build cache key
        key = ("%s_%s" % (self.__class__.__name__, "WORKFLOW")).upper()
        workflow = cache.get(key)
        if workflow is not None:
            return workflow

        workflow = utils.get_workflow(self)
        cache.set(key, workflow)
        return workflow

    def remove_workflow(self):
        """Removes the workflow from the object. After this function has been
        called the object has no *own* workflow anymore (it might have one via
        its content type).

        """
        return utils.remove_workflow_from_object(self)

    def set_workflow(self, workflow):
        """Sets the passed workflow to the object. This will set the local
        workflow for the object.

        If the object has already the given workflow nothing happens.
        Otherwise the object gets the passed workflow and the state is set to
        the workflow's initial state.

        **Parameters:**

        workflow
            The workflow which should be set to the object. Can be a Workflow
            instance or a string with the workflow name.
        obj
            The object which gets the passed workflow.
        """
        return utils.set_workflow_for_object(self, workflow)

    def get_state(self):
        """Returns the current workflow state of the object.
        """
        return utils.get_state(self)

    def get_state_name(self):
        """Returns the current workflow state name of the object.
        """
        return str(utils.get_state(self))

    def set_state(self, state):
        """Sets the workflow state of the object.
        """
        return utils.set_state(self, state)

    def set_initial_state(self):
        """Sets the initial state of the current workflow to the object.
        """
        return self.set_state(self.get_workflow().initial_state)

    def get_allowed_transitions(self, user):
        """Returns allowed transitions for the current state.
        """
        return utils.get_allowed_transitions(self, user)

    def do_transition(self, transition, user, comment=None):
        """Processes the passed transition (if allowed).
        """
        success = utils.do_transition(self, transition, user)
        if success:
            # update current state
            self.current_state = transition.destination
            self.save()

            # save history
            WorkflowHistorical.objects.create(
                content_type=self.get_content_type(),
                content_id=self.pk,
                state=transition.destination,
                transition=transition,
                user=user,
                comment=comment
            )
        return success

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, comment=u"", user=None):
        """
        Overriding the model save method in order to save the initial history workflow
        """
        new_instance = True if not self.pk else False
        if new_instance:
            self.current_state = self.get_workflow().initial_state

        Model.save(self, force_insert, force_update, using, update_fields)

        if new_instance and self.pk:
            self.set_initial_state()
            # save history
            WorkflowHistorical.objects.create(
                content_type=self.get_content_type(),
                content_id=self.pk,
                state=self.current_state,
                user=user,
                comment=comment
            )

        # fix user roles
        self.fix_user_roles()

    def get_content_type(self):
        """
        Returns self content type
        """
        # build cache key
        key = ("%s_%s" % (self.__class__.__name__, "C_TYPE")).upper()
        content_type = cache.get(key)
        if content_type is not None:
            return content_type

        content_type = ContentType.objects.get_for_model(self)
        cache.set(key, content_type)
        return content_type

    def fix_user_roles(self):
        """
        Fix the user roles with self instance defined in the workflow settings
        """
        workflows = getattr(settings, 'WORKFLOWS', {})
        wf_name = self.get_workflow().name
        model_path = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        # finding workflow settings
        wf_item = workflows.get(model_path, None)
        if wf_item:
            user_roles = get_wf_dict_value(wf_item, 'user_roles', wf_name)
            for user_role in user_roles:
                user_path = get_wf_dict_value(user_role, 'user_path', wf_name, 'user_roles')
                role = get_wf_dict_value(user_role, 'role', wf_name, 'user_roles')

                attributes = user_path.split('.')
                target = self
                for attr in attributes:
                    try:
                        target = getattr(target, attr)
                    except AttributeError:
                        target = None
                        break
                else:
                    if not target:
                        continue  # go to the next user_role

                if inspect.ismethod(target):
                    target = target()

                # add (user or group) role relation
                if isinstance(target, Iterable):
                    for item in target:
                        self._add_user_group_role(item, Role.objects.get(name=role))
                else:
                    self._add_user_group_role(target, Role.objects.get(name=role))

    def _add_user_group_role(self, target, role):
        if isinstance(target, User) or isinstance(target, Group):
            add_local_role(self, target, role)
        else:
            raise TypeError('Expected a django User or Group instance.')


# BUILDING WORKFLOWS

# django imports
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_by_path
from django.db.transaction import atomic

# workflow imports
from workflows import models as workflow_app
from workflows.models import Workflow, State, StatePermissionRelation, WorkflowPermissionRelation, Transition

# permission imports
from permissions import utils as perm_utils
from permissions.models import Permission, Role


@atomic
def get_or_create_workflow(model):
    """
    Iterate for the application workflow list and configure each workflow listed in WORKFLOWS settings
    """
    try:
        workflow = utils.get_workflow_for_model(ContentType.objects.get_for_model(model))

        if not workflow:
            workflows_settings = getattr(settings, 'WORKFLOWS', {})
            model_path = "%s.%s" % (model.__module__, model.__name__)
            wf_item = workflows_settings.get(model_path, None)

            try:
                wf_name = wf_item['name']

                # ROLES
                dict_roles = {}
                roles = get_wf_dict_value(wf_item, 'roles', wf_name)
                for role in roles:
                    dict_roles[role] = perm_utils.register_role(name=role)

                # PERMISSIONS
                dict_permissions = {}
                permissions = get_wf_dict_value(wf_item, 'permissions', wf_name)

                for permission in permissions:
                    perm_name = get_wf_dict_value(permission, 'name', 'permissions', wf_name)
                    perm_codename = get_wf_dict_value(permission, 'codename', 'permissions', wf_name)

                    dict_permissions[perm_codename] = perm_utils.register_permission(
                        name=perm_name,
                        codename=perm_codename
                    )
                    # the permission registration returned False if the permission already exists
                    if not dict_permissions[perm_codename]:
                        dict_permissions[perm_codename] = Permission.objects.get(name=perm_name, codename=perm_codename)

                # creating workflow
                workflow = Workflow.objects.create(name=wf_name)
                # setting model
                workflow.set_to_model(ContentType.objects.get_for_model(model))

                dict_states = {}
                # INITIAL STATE
                initial_state = get_wf_dict_value(wf_item, 'initial_state', wf_name)
                initial_state_name = get_wf_dict_value(initial_state, 'name', wf_name, 'initial_state')
                initial_state_alias = initial_state.get('alias', None)

                wf_initial_state = State.objects.create(name=initial_state_name, alias=initial_state_alias, workflow=workflow)
                dict_states[initial_state_name] = wf_initial_state
                # sets and save the initial state
                workflow.initial_state = wf_initial_state
                workflow.save()

                state_perm_relations = initial_state.get('state_perm_relation', False)
                # if [True] creates the State Permission Relation
                if state_perm_relations:
                    for state_perm_relation in state_perm_relations:
                        role = get_wf_dict_value(state_perm_relation, 'role', wf_name, 'state_perm_relation')
                        permission = get_wf_dict_value(state_perm_relation, 'permission', wf_name, 'state_perm_relation')
                        StatePermissionRelation.objects.get_or_create(
                            state=wf_initial_state,
                            role=get_wf_dict_value(dict_roles, role, wf_name, 'dict_roles'),
                            permission=get_wf_dict_value(dict_permissions, permission, wf_name, 'dict_permissions')
                        )

                # STATES
                states = get_wf_dict_value(wf_item, 'states', wf_name)
                for state in states:
                    state_name = get_wf_dict_value(state, 'name', wf_name, 'states')
                    state_alias = state.get('alias', None)

                    wf_state = State.objects.create(name=state_name, alias=state_alias, workflow=workflow)
                    dict_states[state_name] = wf_state

                    state_perm_relations = state.get('state_perm_relation', False)
                    # if [True] creates the State Permission Relation
                    if state_perm_relations:
                        for state_perm_relation in state_perm_relations:
                            role = get_wf_dict_value(state_perm_relation, 'role', wf_name, 'state_perm_relation')
                            permission = get_wf_dict_value(state_perm_relation, 'permission', wf_name, 'state_perm_relation')
                            StatePermissionRelation.objects.get_or_create(
                                state=wf_state,
                                role=get_wf_dict_value(dict_roles, role, wf_name, 'dict_roles'),
                                permission=get_wf_dict_value(dict_permissions, permission, wf_name, 'dict_permissions')
                            )

                # creating the Workflow Permission Relation
                for wf_permission in dict_permissions.itervalues():
                    WorkflowPermissionRelation.objects.get_or_create(workflow=workflow, permission=wf_permission)

                # TRANSITIONS
                dict_transitions = {}
                transitions = get_wf_dict_value(wf_item, 'transitions', wf_name)
                for transition in transitions:
                    name = get_wf_dict_value(transition, 'name', wf_name, 'transitions')
                    destination = get_wf_dict_value(transition, 'destination', wf_name, 'transitions')
                    permission = get_wf_dict_value(transition, 'permission', wf_name, 'transitions')

                    wf_transition, created = Transition.objects.get_or_create(
                        name=name,
                        workflow=workflow,
                        destination=get_wf_dict_value(dict_states, destination, wf_name, 'dict_states'),
                        permission=get_wf_dict_value(dict_permissions, permission, wf_name, 'dict_permissions'),
                        description=get_wf_dict_value(transition, 'description', wf_name, 'transitions'),
                        condition=transition.get('condition', ''),
                    )

                    dict_transitions[name] = wf_transition

                # CREATING THE STATE TRANSITIONS RELATION
                state_transitions = get_wf_dict_value(wf_item, 'state_transitions', wf_name)
                for state_name, transitions in state_transitions.items():
                    state = get_wf_dict_value(dict_states, state_name, wf_name, 'dict_states')

                    for transition_name in transitions:
                        transition = get_wf_dict_value(dict_transitions, transition_name, wf_name, 'dict_transitions')
                        state.transitions.add(transition)

            except KeyError:
                raise ImproperlyConfigured('The attribute or key (name), must be specified in the workflow configuration.')

        return workflow

    except:
        return None


def get_wf_dict_value(dictionary, key, wf_name, parent_name=None):
    """
    Returns the value of the dict related with the specific key or raise a KeyError exception

    :param dictionary: a django dictionary
    :param key: a django dictionary key
    :param wf_name: workflow name
    :param parent_name: edge parent name
    """
    try:
        return dictionary[key]
    except KeyError:
        if not parent_name:
            raise ImproperlyConfigured(
                'The attribute or key (%s), must be specified in the workflow(%s) configuration.' % (key, wf_name)
            )
        else:
            raise ImproperlyConfigured(
                'The attribute or key (%s), must be specified in the %s configuration. '
                'Associated with workflow (%s).' % (key, parent_name, wf_name)
            )