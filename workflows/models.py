# coding=utf-8
import inspect
from collections import Iterable
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import models
from django.core.cache import cache
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

import permissions.utils
from permissions.models import Permission, Role

import utils


class WorkflowManager(models.Manager):

    def get_by_natural_key(self, name):
        return self.get(name=name)


class Workflow(models.Model):
    """A workflow consists of a sequence of connected (through transitions)
    states. It can be assigned to a model and / or model instances. If a
    model instance has a workflow it takes precendence over the model's
    workflow.

    **Attributes:**

    model
        The model the workflow belongs to. Can be any

    content
        The object the workflow belongs to.

    name
        The unique name of the workflow.

    states
        The states of the workflow.

    initial_state
        The initial state the model / content gets if created.

    """
    name = models.CharField(_(u"Name"), max_length=100, unique=True)
    initial_state = models.ForeignKey("State", related_name="workflow_state", blank=True, null=True)
    permissions = models.ManyToManyField(Permission, symmetrical=False, through="WorkflowPermissionRelation")
    objects = WorkflowManager()

    def __unicode__(self):
        return self.name

    def natural_key(self):
        return self.name,


    def get_initial_state(self):
        """Returns the initial state of the workflow. Takes the first one if
        no state has been defined.
        """
        if self.initial_state:
            return self.initial_state
        else:
            try:
                return self.states.all()[0]
            except IndexError:
                return None

    def get_objects(self):
        """Returns all objects which have this workflow assigned. Globally
        (via the object's content type) or locally (via the object itself).
        """
        import utils
        objs = []

        # Get all objects whose content type has this workflow
        for wmr in WorkflowModelRelation.objects.filter(workflow=self):
            ctype = wmr.content_type
            # We have also to check whether the global workflow is not
            # overwritten.
            for obj in ctype.model_class().objects.all():
                if utils.get_workflow(obj) == self:
                    objs.append(obj)

        # Get all objects whose local workflow this workflow
        for wor in WorkflowObjectRelation.objects.filter(workflow=self):
            if wor.content not in objs:
                objs.append(wor.content)

        return objs

    def set_to(self, ctype_or_obj):
        """Sets the workflow to passed content type or object. See the specific
        methods for more information.

        **Parameters:**

        ctype_or_obj
            The content type or the object to which the workflow should be set.
            Can be either a ContentType instance or any Django model instance.
        """
        if isinstance(ctype_or_obj, ContentType):
            return self.set_to_model(ctype_or_obj)
        else:
            return self.set_to_object(ctype_or_obj)

    def set_to_model(self, ctype):
        """Sets the workflow to the passed content type. If the content
        type has already an assigned workflow the workflow is overwritten.

        **Parameters:**

        ctype
            The content type which gets the workflow. Can be any Django model
            instance.
        """
        try:
            wor = WorkflowModelRelation.objects.get(content_type=ctype)
        except WorkflowModelRelation.DoesNotExist:
            WorkflowModelRelation.objects.create(content_type=ctype, workflow=self)
        else:
            wor.workflow = self
            wor.save()

    def set_to_object(self, obj):
        """Sets the workflow to the passed object.

        If the object has already the given workflow nothing happens. Otherwise
        the workflow is set to the objectthe state is set to the workflow's
        initial state.

        **Parameters:**

        obj
            The object which gets the workflow.
        """
        import utils

        ctype = ContentType.objects.get_for_model(obj)
        try:
            wor = WorkflowObjectRelation.objects.get(content_type=ctype, content_id=obj.id)
        except WorkflowObjectRelation.DoesNotExist:
            WorkflowObjectRelation.objects.create(content = obj, workflow=self)
            utils.set_state(obj, self.initial_state)
        else:
            if wor.workflow != self:
                wor.workflow = self
                wor.save()
                utils.set_state(self.initial_state)


class State(models.Model):
    """A certain state within workflow.

    **Attributes:**

    name
        The unique name of the state within the workflow.

    workflow
        The workflow to which the state belongs.

    transitions
        The transitions of a workflow state.

    """
    name = models.CharField(_(u"Name"), max_length=100)
    alias = models.CharField(_(u"Alias"), max_length=100, blank=True, null=True)
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="states")
    transitions = models.ManyToManyField("Transition", verbose_name=_(u"Transitions"), blank=True, null=True, related_name="states")

    class Meta:
        ordering = ("name", )
        unique_together = ('name', 'workflow')

    def __unicode__(self):
        return "%s (%s)" % (self.alias if self.alias else self.name, self.workflow.name)

    def get_allowed_transitions(self, obj, user):
        """Returns all allowed transitions for passed object and user.
        """
        transitions = []
        for transition in self.transitions.all():
            permission = transition.permission
            if permission is None:
                transitions.append(transition)
            else:
                # First we try to get the objects specific has_permission
                # method (in case the object inherits from the PermissionBase
                # class).
                try:
                    if obj.has_permission(user, permission.codename):
                        transitions.append(transition)
                except AttributeError:
                    if permissions.utils.has_permission(obj, user, permission.codename):
                        transitions.append(transition)
        return transitions


class Transition(models.Model):
    """A transition from a source to a destination state. The transition can
    be used from several source states.

    **Attributes:**

    name
        The unique name of the transition within a workflow.

    workflow
        The workflow to which the transition belongs. Must be a Workflow
        instance.

    destination
        The state after a transition has been processed. Must be a State
        instance.

    condition
        The condition when the transition is available. Can be any python
        expression.

    permission
        The necessary permission to process the transition. Must be a
        Permission instance.

    description
        The description of the transition within a workflow.

    """
    name = models.CharField(_(u"Name"), max_length=100)
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="transitions")
    destination = models.ForeignKey(State, verbose_name=_(u"Destination"), null=True, blank=True, related_name="destination_state")
    condition = models.CharField(_(u"Condition"), blank=True, max_length=100)
    permission = models.ForeignKey(Permission, verbose_name=_(u"Permission"), blank=True, null=True)
    description = models.CharField(_(u"Description"), max_length=1000, null=True, blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'workflow')


class StateObjectRelation(models.Model):
    """Stores the workflow state of an object.

    Provides a way to give any object a workflow state without changing the
    object's model.

    **Attributes:**

    content
        The object for which the state is stored. This can be any instance of
        a Django model.

    state
        The state of content. This must be a State instance.
    """
    content_type = models.ForeignKey(ContentType, verbose_name=_(u"Content type"), related_name="state_object", blank=True, null=True)
    content_id = models.PositiveIntegerField(_(u"Content id"), blank=True, null=True)
    content = generic.GenericForeignKey(ct_field="content_type", fk_field="content_id")
    state = models.ForeignKey(State, verbose_name = _(u"State"))

    def __unicode__(self):
        return "%s %s - %s" % (self.content_type.name, self.content_id, self.state.name)

    class Meta:
        unique_together = ("content_type", "content_id", "state")


class WorkflowObjectRelation(models.Model):
    """Stores an workflow of an object.

    Provides a way to give any object a workflow without changing the object's
    model.

    **Attributes:**

    content
        The object for which the workflow is stored. This can be any instance of
        a Django model.

    workflow
        The workflow which is assigned to an object. This needs to be a workflow
        instance.
    """
    content_type = models.ForeignKey(ContentType, verbose_name=_(u"Content type"), related_name="workflow_object", blank=True, null=True)
    content_id = models.PositiveIntegerField(_(u"Content id"), blank=True, null=True)
    content = generic.GenericForeignKey(ct_field="content_type", fk_field="content_id")
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="wors")

    class Meta:
        unique_together = ("content_type", "content_id")

    def __unicode__(self):
        return "%s %s - %s" % (self.content_type.name, self.content_id, self.workflow.name)


class WorkflowModelRelation(models.Model):
    """Stores an workflow for a model (ContentType).

    Provides a way to give any object a workflow without changing the model.

    **Attributes:**

    Content Type
        The content type for which the workflow is stored. This can be any
        instance of a Django model.

    workflow
        The workflow which is assigned to an object. This needs to be a
        workflow instance.
    """
    content_type = models.ForeignKey(ContentType, verbose_name=_(u"Content Type"), unique=True)
    workflow = models.ForeignKey(Workflow, verbose_name=_(u"Workflow"), related_name="wmrs")

    def __unicode__(self):
        return "%s - %s" % (self.content_type.name, self.workflow.name)


# Permissions relation #######################################################
class WorkflowPermissionRelation(models.Model):
    """Stores the permissions for which a workflow is responsible.

    **Attributes:**

    workflow
        The workflow which is responsible for the permissions. Needs to be a
        Workflow instance.

    permission
        The permission for which the workflow is responsible. Needs to be a
        Permission instance.
    """
    workflow = models.ForeignKey(Workflow)
    permission = models.ForeignKey(Permission, related_name="permissions")

    class Meta:
        unique_together = ("workflow", "permission")

    def __unicode__(self):
        return "%s %s" % (self.workflow.name, self.permission.name)


class StateInheritanceBlock(models.Model):
    """Stores inheritance block for state and permission.

    **Attributes:**

    state
        The state for which the inheritance is blocked. Needs to be a State
        instance.

    permission
        The permission for which the instance is blocked. Needs to be a
        Permission instance.
    """
    state = models.ForeignKey(State, verbose_name=_(u"State"))
    permission = models.ForeignKey(Permission, verbose_name=_(u"Permission"))

    def __unicode__(self):
        return "%s %s" % (self.state.name, self.permission.name)


class StatePermissionRelation(models.Model):
    """Stores granted permission for state and role.

    **Attributes:**

    state
        The state for which the role has the permission. Needs to be a State
        instance.

    permission
        The permission for which the workflow is responsible. Needs to be a
        Permission instance.

    role
        The role for which the state has the permission. Needs to be a lfc
        Role instance.
    """
    state = models.ForeignKey(State, verbose_name=_(u"State"))
    permission = models.ForeignKey(Permission, verbose_name=_(u"Permission"))
    role = models.ForeignKey(Role, verbose_name=_(u"Role"))

    def __unicode__(self):
        return "%s %s %s" % (self.state.name, self.role.name, self.permission.name)


class WorkflowHistoricalManager(models.Manager):
    """
        WorkflowHistoricalManager class.
    """

    def get_history_from_object_query_set(self, obj):
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=content_type, content_id=obj.pk)

    def get_elements_for_user(self, obj, user):
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=content_type, content_id=obj.id, user=user)


class WorkflowHistorical(models.Model):
    """ Model class to save the historic of workflow.

    **Attributes:**

    content_type
        The content type for the related workflow stored. This can be any
        instance of a Django model.

    content
        The object for the related workflow stored. This can be any instance of
        a Django model.

    user
        The user implicated with the workflow change. Needs to be a django
        AbstractUser instance.

    state
        The current state after the workflow is changed. Needs to be a
        State instance.

    transition
        The executed transition to change the workflow. Needs to be a
        Transition instance.

    update_at
        The datetime of the workflow modification. Needs to be a
        DateTimeField instance.

    comment
        The comment related with the workflow modification. Needs to be a
        DateTimeField instance.
    """
    content_type = models.ForeignKey(
        ContentType,
        verbose_name=_(u"Content type"),
        related_name="content_type_set_for_%(class)s"
    )
    content_id = models.PositiveIntegerField(_(u"Content id"))
    content = generic.GenericForeignKey('content_type', 'content_id')

    user = models.ForeignKey(User, verbose_name=_(u"User"), null=True, blank=True)
    state = models.ForeignKey(State, verbose_name=_(u"Current state"))
    transition = models.ForeignKey(Transition, verbose_name=_(u"Transition"), blank=True, null=True)
    update_at = models.DateTimeField(_(u"Update at"), auto_now_add=True)
    comment = models.TextField(_(u"User comment"), null=True, blank=True)

    objects = WorkflowHistoricalManager()


class WorkflowBase(models.Model):
    """Mixin class to make objects workflow aware.
    """

    class Meta(object):
        abstract = True

    @classmethod
    def workflow(cls):
        return utils.get_or_create_workflow(cls)

    @classmethod
    def states(cls):
        return cls.workflow().states.all()

    @classmethod
    def final_states(cls):
        return cls.states().filter(transitions=None)

    @classmethod
    def active_states(cls):
        return cls.states().exclude(transitions=None)

    def get_workflow(self):
        """Returns the current workflow of the object.
        """
        # build cache key
        key = ("%s_%s" % (self.__class__.__name__, "WORKFLOW")).upper()
        workflow = cache.get(key)
        if workflow is not None:
            return workflow

        workflow = utils.get_workflow(self)
        if workflow:
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
        if not isinstance(transition, Transition):
            try:
                transition = Transition.objects.get(name=transition, workflow=self.get_workflow())
            except Transition.DoesNotExist:
                return False

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

        models.Model.save(self, force_insert, force_update, using, update_fields)

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
            user_roles = utils.get_wf_dict_value(wf_item, 'user_roles', wf_name)
            for user_role in user_roles:
                user_path = utils.get_wf_dict_value(user_role, 'user_path', wf_name, 'user_roles')
                role = utils.get_wf_dict_value(user_role, 'role', wf_name, 'user_roles')

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
            permissions.utils.add_local_role(self, target, role)
        else:
            raise TypeError('Expected a django User or Group instance.')

    def history(self, recent_first=True):
        versions = WorkflowHistorical.objects.get_history_from_object_query_set(self)
        if recent_first:
            versions = versions.order_by('-update_at')
        else:
            versions = versions.order_by('update_at')
        return (version for version in versions)

    def reverse_history(self):
        return self.history(recent_first=False)