# coding=utf-8
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.transaction import atomic

from permissions.models import ObjectPermission, Permission, Role
from permissions import utils as perm_utils


@atomic
def get_or_create_workflow(model):
    """
    Iterate for the application workflow list and configure each workflow listed in WORKFLOWS settings
    """
    from models import State, Workflow, StatePermissionRelation, WorkflowPermissionRelation, Transition

    try:
        workflow = get_workflow_for_model(ContentType.objects.get_for_model(model))
    except Exception as e:
        return None

    if not workflow:
        workflows_settings = getattr(settings, 'WORKFLOWS', {})
        wf_item = workflows_settings.get("%s.%s" % (model.__module__, model.__name__), None)

        if not wf_item:
            return None

        try:
            wf_name = wf_item['name']

            # ROLES
            dict_roles = {}
            roles = get_wf_dict_value(wf_item, 'roles', wf_name)
            for role in roles:
                dict_roles[role], created = Role.objects.get_or_create(name=role)

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


def get_objects_for_workflow(workflow):
    """Returns all objects which have passed workflow.

    **Parameters:**

    workflow
        The workflow for which the objects are returned. Can be a Workflow
        instance or a string with the workflow name.
    """
    from models import Workflow

    if not isinstance(workflow, Workflow):
        try:
            workflow = Workflow.objects.get(name=workflow)
        except Workflow.DoesNotExist:
            return []

    return workflow.get_objects()


def remove_workflow(ctype_or_obj):
    """Removes the workflow from the passed content type or object. After this
    function has been called the content type or object has no workflow
    anymore.

    If ctype_or_obj is an object the workflow is removed from the object not
    from the belonging content type.

    If ctype_or_obj is an content type the workflow is removed from the
    content type not from instances of the content type (if they have an own
    workflow)

    ctype_or_obj
        The content type or the object to which the passed workflow should be
        set. Can be either a ContentType instance or any LFC Django model
        instance.
    """
    if isinstance(ctype_or_obj, ContentType):
        remove_workflow_from_model(ctype_or_obj)
    else:
        remove_workflow_from_object(ctype_or_obj)


def remove_workflow_from_model(ctype):
    """Removes the workflow from passed content type. After this function has
    been called the content type has no workflow anymore (the instances might
    have own ones).

    ctype
        The content type from which the passed workflow should be removed.
        Must be a ContentType instance.
    """
    # First delete all states, inheritance blocks and permissions from ctype's
    # instances which have passed workflow.
    from models import StateObjectRelation, WorkflowModelRelation

    workflow = get_workflow_for_model(ctype)
    for obj in get_objects_for_workflow(workflow):
        try:
            ctype = ContentType.objects.get_for_model(obj)
            sor = StateObjectRelation.objects.get(content_id=obj.id, content_type=ctype)
        except StateObjectRelation.DoesNotExist:
            pass
        else:
            sor.delete()

        # Reset all permissions
        perm_utils.reset(obj)

    try:
        wmr = WorkflowModelRelation.objects.get(content_type=ctype)
    except WorkflowModelRelation.DoesNotExist:
        pass
    else:
        wmr.delete()


def remove_workflow_from_object(obj):
    """Removes the workflow from the passed object. After this function has
    been called the object has no *own* workflow anymore (it might have one
    via its content type).

    obj
        The object from which the passed workflow should be set. Must be a
        Django Model instance.
    """
    from models import WorkflowObjectRelation

    try:
        wor = WorkflowObjectRelation.objects.get(content_type=obj)
    except WorkflowObjectRelation.DoesNotExist:
        pass
    else:
        wor.delete()

    # Reset all permissions
    perm_utils.reset(obj)

    # Set initial of object's content types workflow (if there is one)
    set_initial_state(obj)


def set_workflow(ctype_or_obj, workflow):
    """Sets the workflow for passed content type or object. See the specific
    methods for more information.

    **Parameters:**

    workflow
        The workflow which should be set to the object or model.

    ctype_or_obj
        The content type or the object to which the passed workflow should be
        set. Can be either a ContentType instance or any Django model
        instance.
    """
    return workflow.set_to(ctype_or_obj)


def set_workflow_for_object(obj, workflow):
    """Sets the passed workflow to the passed object.

    If the object has already the given workflow nothing happens. Otherwise
    the object gets the passed workflow and the state is set to the workflow's
    initial state.

    **Parameters:**

    workflow
        The workflow which should be set to the object. Can be a Workflow
        instance or a string with the workflow name.

    obj
        The object which gets the passed workflow.
    """
    from models import Workflow

    if isinstance(workflow, Workflow) == False:
        try:
            workflow = Workflow.objects.get(name=workflow)
        except Workflow.DoesNotExist:
            return False

    workflow.set_to_object(obj)


def set_workflow_for_model(ctype, workflow):
    """Sets the passed workflow to the passed content type. If the content
    type has already an assigned workflow the workflow is overwritten.

    The objects which had the old workflow must updated explicitely.

    **Parameters:**

    workflow
        The workflow which should be set to passend content type. Must be a
        Workflow instance.

    ctype
        The content type to which the passed workflow should be assigned. Can
        be any Django model instance
    """
    from models import Workflow

    if isinstance(workflow, Workflow) == False:
        try:
            workflow = Workflow.objects.get(name=workflow)
        except Workflow.DoesNotExist:
            return False

    workflow.set_to_model(ctype)


def get_workflow(obj):
    """Returns the workflow for the passed object. It takes it either from
    the passed object or - if the object doesn't have a workflow - from the
    passed object's ContentType.

    **Parameters:**

    object
        The object for which the workflow should be returend. Can be any
        Django model instance.
    """
    workflow = get_workflow_for_object(obj)
    if workflow is not None:
        return workflow

    return get_or_create_workflow(obj.__class__)


def get_workflow_for_object(obj):
    """Returns the workflow for the passed object.

    **Parameters:**

    obj
        The object for which the workflow should be returned. Can be any
        Django model instance.
    """
    from models import WorkflowObjectRelation

    try:
        ctype = ContentType.objects.get_for_model(obj)
        wor = WorkflowObjectRelation.objects.get(content_id=obj.id, content_type=ctype)
    except WorkflowObjectRelation.DoesNotExist:
        return None
    else:
        return wor.workflow


def get_workflow_for_model(ctype):
    """Returns the workflow for the passed model.

    **Parameters:**

    ctype
        The content type for which the workflow should be returned. Must be
        a Django ContentType instance.
    """
    from models import WorkflowModelRelation

    try:
        wor = WorkflowModelRelation.objects.get(content_type=ctype)
    except WorkflowModelRelation.DoesNotExist:
        return None
    else:
        return wor.workflow


def get_state(obj):
    """Returns the current workflow state for the passed object.

    **Parameters:**

    obj
        The object for which the workflow state should be returned. Can be any
        Django model instance.
    """
    from models import StateObjectRelation, WorkflowModelRelation

    ctype = ContentType.objects.get_for_model(obj)
    try:
        sor = StateObjectRelation.objects.get(content_type=ctype, content_id=obj.id)
    except StateObjectRelation.DoesNotExist:
        return None
    else:
        return sor.state


def set_state(obj, state):
    """Sets the state for the passed object to the passed state and updates
    the permissions for the object.

    **Parameters:**

    obj
        The object for which the workflow state should be set. Can be any
        Django model instance.

    state
        The state which should be set to the passed object.
    """
    from models import StateObjectRelation

    ctype = ContentType.objects.get_for_model(obj)
    try:
        sor = StateObjectRelation.objects.get(content_type=ctype, content_id=obj.id)
    except StateObjectRelation.DoesNotExist:
        sor = StateObjectRelation.objects.create(content=obj, state=state)
    else:
        sor.state = state
        sor.save()
    update_permissions(obj)


def set_initial_state(obj):
    """Sets the initial state to the passed object.
    """
    wf = get_workflow(obj)
    if wf is not None:
        set_state(obj, wf.get_initial_state())


def get_allowed_transitions(obj, user):
    """Returns all allowed transitions for passed object and user. Takes the
    current state of the object into account.

    **Parameters:**

    obj
        The object for which the transitions should be returned.

    user
        The user for which the transitions are allowed.
    """
    state = obj.current_state or get_state(obj)
    if state is None:
        return []

    return state.get_allowed_transitions(obj, user)


def do_transition(obj, transition, user):
    """Processes the passed transition to the passed object (if allowed).
    """
    transitions = get_allowed_transitions(obj, user)
    if transition in transitions:
        set_state(obj, transition.destination)
        return True
    else:
        return False


def update_permissions(obj):
    """Updates the permissions of the passed object according to the object's
    current workflow state.
    """
    from models import StatePermissionRelation

    workflow = get_workflow(obj)
    model_path = "%s.%s" % (obj.__class__.__module__, obj.__class__.__name__)
    # finding workflow settings
    workflows = getattr(settings, 'WORKFLOWS', {})
    workflow_dict = workflows.get(model_path, None)

    if workflow_dict:
        state = obj.current_state or get_state(obj)
        ct = ContentType.objects.get_for_model(obj)
        roles = workflow_dict['roles']

        # Remove all permissions for the workflow
        ObjectPermission.objects.filter(
            role__name__in=roles,
            content_type=ct,
            content_id=obj.id,
            permission__workflow_permissions__workflow=workflow
        ).delete()

        # Grant permission for the state
        object_permission_list = []
        for spr in StatePermissionRelation.objects.filter(state=state):
            object_permission_list.append(ObjectPermission(
                role=spr.role,
                content_type=ct,
                content_id=obj.id,
                permission=spr.permission
            ))
        ObjectPermission.objects.bulk_create(object_permission_list)

        # Remove all inheritance blocks from the object
        # for wpr in WorkflowPermissionRelation.objects.filter(workflow=workflow):
        #     permissions.utils.remove_inheritance_block(obj, wpr.permission)
        #
        # # Add inheritance blocks of this state to the object
        # for sib in StateInheritanceBlock.objects.filter(state=state):
        #     permissions.utils.add_inheritance_block(obj, sib.permission)