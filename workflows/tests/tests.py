# coding=utf-8

# django imports
from django.contrib.contenttypes.models import ContentType
from django.contrib.flatpages.models import FlatPage
from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib.sessions.backends.file import SessionStore
from django.core.handlers.wsgi import WSGIRequest
from django.test.client import Client

# workflows import
import permissions.utils
from workflows import utils
from workflows.models import (
    Workflow,
    WorkflowModelRelation,
    WorkflowObjectRelation,
    WorkflowPermissionRelation,
    State,
    StatePermissionRelation,
    StateObjectRelation,
    Transition
)
from workflows.tests.models import Publication


# Extended of django-workflow tests and adapted to django-wflow
class WorkflowTestCase(TestCase):
    """Tests a simple workflow without permissions.
    """
    def setUp(self):
        """
        """
        self.publication = create_publication()
        self.workflow = self.publication.get_workflow()

        self.private = "Private"
        self.public = "Public"

    def test_get_states(self):
        """
        """
        states = self.workflow.states.all()
        self.assertEqual(states[0].name, self.private)
        self.assertEqual(states[1].name, self.public)

    def test_unicode(self):
        """
        """
        self.assertEqual(self.workflow.__unicode__(), u"PUBLICATION_WORKFLOW")


# Extended of django-workflow tests and adapted to django-wflow
class PermissionsTestCase(TestCase):
    """Tests a simple workflow with permissions.
    """
    def setUp(self):
        """
        """
        self.publication = create_publication()
        self.workflow = self.publication.get_workflow()
        self.user = self.publication.owner

        self.private = State.objects.get(name='Private')
        self.public = State.objects.get(name='Public')

    def test_set_state(self):
        """
        """
        # Permissions
        self.assertEqual(permissions.utils.has_permission(self.publication, self.user, "edit"), True)

        self.assertEqual(permissions.utils.has_permission(self.publication, self.user, "view"), True)

        # # Inheritance
        # self.assertEqual(permissions.utils.is_inherited(self.publication, "view"), False)
        #
        # self.assertEqual(permissions.utils.is_inherited(self.publication, "edit"), False)

        # Change state
        self.publication.set_state(self.public)

        # Permissions
        self.assertEqual(permissions.utils.has_permission(self.publication, self.user, "edit"), False)

        self.assertEqual(permissions.utils.has_permission(self.publication, self.user, "view"), True)

        # # Inheritance
        # self.assertEqual(permissions.utils.is_inherited(self.publication, "view"), True)
        #
        # self.assertEqual(permissions.utils.is_inherited(self.publication, "edit"), False)

    def test_set_initial_state(self):
        """
        """
        self.assertEqual(self.publication.current_state.name, self.private.name)

        self.publication.do_make_public(self.user)
        self.assertEqual(self.publication.current_state.name, self.public.name)

        self.publication.set_initial_state()
        self.assertEqual(self.publication.get_state().name, self.private.name)

    def test_do_transition(self):
        """
        """
        self.assertEqual(self.publication.current_state.name, self.private.name)

        # by transition
        self.publication.do_make_public(self.user)

        self.assertEqual(self.publication.current_state.name, self.public.name)

        # by name
        self.publication.do_make_private(self.user)

        self.assertEqual(self.publication.current_state.name, self.private.name)

        # name which does not exist
        result = utils.do_transition(self.publication, "Make pending", self.user)
        self.assertEqual(result, False)

        wrong = Transition.objects.create(name="Wrong", workflow=self.workflow, destination=self.public)

        # name which does not exist
        result = utils.do_transition(self.publication, wrong, self.user)
        self.assertEqual(result, False)


# Extended of django-workflow tests and adapted to django-wflow
class UtilsTestCase(TestCase):
    """Tests various methods of the utils module.
    """
    def setUp(self):
        """
        """
        self.publication = create_publication()
        self.workflow = self.publication.get_workflow()
        self.user = User.objects.create()

        self.private = State.objects.get(name='Private')
        self.public = State.objects.get(name='Public')

    def test_workflow(self):
        """
        """
        utils.set_workflow(self.user, self.workflow)
        result = utils.get_workflow(self.user)
        self.assertEqual(result, self.workflow)

    def test_state(self):
        """
        """
        result = utils.get_state(self.user)
        self.assertEqual(result, None)

        utils.set_workflow(self.user, self.workflow)
        result = utils.get_state(self.user)
        self.assertEqual(result, self.workflow.initial_state)

    def test_set_workflow_1(self):
        """Set worklow by object
        """
        ctype = ContentType.objects.get_for_model(self.user)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, None)

        wp = Workflow.objects.create(name="Portal")

        # Set for model
        utils.set_workflow_for_model(ctype, wp)

        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, wp)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, wp)

        # Set for object
        utils.set_workflow_for_object(self.user, self.workflow)
        result = utils.get_workflow(self.user)
        self.assertEqual(result, self.workflow)

        # The model still have wp
        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, wp)

    def test_set_workflow_2(self):
        """Set worklow by name
        """
        ctype = ContentType.objects.get_for_model(self.user)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, None)

        wp = Workflow.objects.create(name="Portal")

        # Set for model
        utils.set_workflow_for_model(ctype, "Portal")

        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, wp)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, wp)

        # Set for object
        utils.set_workflow_for_object(self.user, "PUBLICATION_WORKFLOW")
        result = utils.get_workflow(self.user)
        self.assertEqual(result, self.workflow)

        # The model still have wp
        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, wp)

        # Workflow which does not exist
        result = utils.set_workflow_for_model(ctype, "Wrong")
        self.assertEqual(result, False)

        result = utils.set_workflow_for_object(self.user, "Wrong")
        self.assertEqual(result, False)

    def test_get_objects_for_workflow_1(self):
        """Workflow is added to object.
        """
        result = utils.get_objects_for_workflow(self.workflow)
        self.assertEqual(result, [self.publication])

        utils.set_workflow(self.user, self.workflow)
        result = utils.get_objects_for_workflow(self.workflow)
        self.assertEqual(result, [self.publication, self.user])

    def test_get_objects_for_workflow_2(self):
        """Workflow is added to content type.
        """
        result = utils.get_objects_for_workflow(self.workflow)
        self.assertEqual(result, [self.publication])

        ctype = ContentType.objects.get_for_model(self.user)
        utils.set_workflow(ctype, self.workflow)
        result = utils.get_objects_for_workflow(self.workflow)
        self.assertEqual(result, [self.publication, self.publication.owner, self.user])

    def test_get_objects_for_workflow_3(self):
        """Workflow is added to content type and object.
        """
        result = utils.get_objects_for_workflow(self.workflow)
        self.assertEqual(result, [self.publication])

        utils.set_workflow(self.user, self.workflow)
        result = utils.get_objects_for_workflow(self.workflow)
        self.assertEqual(result, [self.publication, self.user])

        ctype = ContentType.objects.get_for_model(self.user)
        utils.set_workflow(ctype, self.workflow)
        result = utils.get_objects_for_workflow(self.workflow)
        self.assertEqual(result, [self.publication, self.publication.owner, self.user])

    def test_get_objects_for_workflow_4(self):
        """Get workflow by name
        """
        result = utils.get_objects_for_workflow("PUBLICATION_WORKFLOW")
        self.assertEqual(result, [self.publication])

        utils.set_workflow(self.user, self.workflow)
        result = utils.get_objects_for_workflow("PUBLICATION_WORKFLOW")
        self.assertEqual(result, [self.publication, self.user])

        # Workflow which does not exist
        result = utils.get_objects_for_workflow("Wrong")
        self.assertEqual(result, [])

    def test_remove_workflow_from_model(self):
        """
        """
        ctype = ContentType.objects.get_for_model(self.user)

        result = utils.get_workflow(ctype)
        self.assertEqual(result, None)

        utils.set_workflow_for_model(ctype, self.workflow)

        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, self.workflow)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, self.workflow)

        utils.remove_workflow_from_model(ctype)

        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, None)

        result = utils.get_workflow_for_object(self.user)
        self.assertEqual(result, None)

    def test_remove_workflow_from_object(self):
        """
        """
        result = utils.get_workflow(self.user)
        self.assertEqual(result, None)

        utils.set_workflow_for_object(self.user, self.workflow)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, self.workflow)

        result = utils.remove_workflow_from_object(self.user)
        self.assertEqual(result, None)

    def test_remove_workflow_1(self):
        """Removes workflow from model
        """
        ctype = ContentType.objects.get_for_model(self.user)

        result = utils.get_workflow(ctype)
        self.assertEqual(result, None)

        utils.set_workflow_for_model(ctype, self.workflow)

        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, self.workflow)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, self.workflow)

        utils.remove_workflow(ctype)

        result = utils.get_workflow_for_model(ctype)
        self.assertEqual(result, None)

        result = utils.get_workflow_for_object(self.user)
        self.assertEqual(result, None)

    def test_remove_workflow_2(self):
        """Removes workflow from object
        """
        result = utils.get_workflow(self.user)
        self.assertEqual(result, None)

        utils.set_workflow_for_object(self.user, self.workflow)

        result = utils.get_workflow(self.user)
        self.assertEqual(result, self.workflow)

        result = utils.remove_workflow(self.user)
        self.assertEqual(result, None)

    def test_get_allowed_transitions(self):
        """Tests get_allowed_transitions method
        """
        publication_2 = Publication.objects.create(name="Publication 2", owner=User.objects.create(username="Aaron"))
        role_1 = permissions.utils.register_role("Role 1")
        permissions.utils.add_role(self.user, role_1)

        view = permissions.utils.register_permission("Publish", "publish")

        transitions = self.private.get_allowed_transitions(publication_2, publication_2.owner)
        self.assertEqual(len(transitions), 1)

        # protect the transition with a permission
        make_public = Transition.objects.get(name="Make public")
        make_public.permission = view
        make_public.save()

        # user has no transition
        transitions = self.private.get_allowed_transitions(publication_2, self.user)
        self.assertEqual(len(transitions), 0)

        # grant permission
        permissions.utils.grant_permission(publication_2, role_1, view)

        # user has transition again
        transitions = self.private.get_allowed_transitions(publication_2, self.user)
        self.assertEqual(len(transitions), 1)

    def test_get_workflow_for_object(self):
        """
        """
        result = utils.get_workflow(self.user)
        self.assertEqual(result, None)

        # Set workflow for a user
        utils.set_workflow_for_object(self.user, self.workflow)

        # Get workflow for the user
        result = utils.get_workflow_for_object(self.user)
        self.assertEqual(result, self.workflow)

        # Set workflow for a FlatPage
        publication_2 = Publication.objects.create(name="Publication 2", owner=User.objects.create(username="Aaron"))
        utils.set_workflow_for_object(publication_2, self.workflow)

        result = utils.get_workflow_for_object(self.user)
        self.assertEqual(result, self.workflow)

        result = utils.get_workflow_for_object(publication_2)
        self.assertEqual(result, self.workflow)


# Extended of django-workflow tests and adapted to django-wflow
class StateTestCase(TestCase):
    """Tests the State model
    """
    def setUp(self):
        """
        """
        self.publication = create_publication()
        self.user = self.publication.owner
        self.role_1 = permissions.utils.register_role("Role 1")
        permissions.utils.add_role(self.user, self.role_1)

        self.private = State.objects.get(name='Private')
        self.public = State.objects.get(name='Public')

    def test_unicode(self):
        """
        """
        self.assertEqual(self.private.__unicode__(), u"Private (PUBLICATION_WORKFLOW)")

    def test_transitions(self):
        """
        """
        transitions = self.public.transitions.all()
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0], Transition.objects.get(name="Make private"))

        transitions = self.private.transitions.all()
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0], Transition.objects.get(name="Make public"))

    def test_get_transitions(self):
        """
        """
        transitions = self.private.get_allowed_transitions(self.publication, self.user)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0], Transition.objects.get(name="Make public"))

        transitions = self.public.get_allowed_transitions(self.publication, self.user)
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0], Transition.objects.get(name="Make private"))

    def test_get_allowed_transitions(self):
        """
        """
        self.view = permissions.utils.register_permission("Publish", "publish")
        transitions = self.private.get_allowed_transitions(self.publication, self.user)
        self.assertEqual(len(transitions), 1)

        # protect the transition with a permission
        make_public = Transition.objects.get(name="Make public")
        make_public.permission = self.view
        make_public.save()

        # user has no transition
        transitions = self.private.get_allowed_transitions(self.publication, self.user)
        self.assertEqual(len(transitions), 0)

        # grant permission
        permissions.utils.grant_permission(self.publication, self.role_1, self.view)

        # user has transition again
        transitions = self.private.get_allowed_transitions(self.publication, self.user)
        self.assertEqual(len(transitions), 1)


# Extended of django-workflow tests and adapted to django-wflow
class TransitionTestCase(TestCase):
    """Tests the Transition model
    """
    def setUp(self):
        """
        """
        create_publication()
        self.make_private = Transition.objects.get(name="Make private")

    def test_unicode(self):
        """
        """
        self.assertEqual(self.make_private.__unicode__(), u"Make private")


# Extended of django-workflow tests and adapted to django-wflow
class RelationsTestCase(TestCase):
    """Tests various Relations models.
    """
    def setUp(self):
        """
        """
        self.publication = create_publication()
        self.workflow = self.publication.get_workflow()

        self.private = State.objects.get(name="Private")
        self.public = State.objects.get(name="Public")

    def test_unicode(self):
        """
        """
        # WorkflowObjectRelation
        utils.set_workflow(self.publication, self.workflow)
        wor = WorkflowObjectRelation.objects.filter()[0]
        self.assertEqual(wor.__unicode__(), "publication 1 - PUBLICATION_WORKFLOW")

        # StateObjectRelation
        utils.set_state(self.publication, self.public)
        sor = StateObjectRelation.objects.filter()[0]
        self.assertEqual(sor.__unicode__(), "publication 1 - Public")

        # WorkflowModelRelation
        ctype = ContentType.objects.get_for_model(self.publication)
        utils.set_workflow(ctype, self.workflow)
        wmr = WorkflowModelRelation.objects.filter()[0]
        self.assertEqual(wmr.__unicode__(), "publication - PUBLICATION_WORKFLOW")

        # WorkflowPermissionRelation
        self.detail = permissions.utils.register_permission("Detail", "detail")
        wpr = WorkflowPermissionRelation.objects.create(workflow=self.workflow, permission=self.detail)
        self.assertEqual(wpr.__unicode__(), "PUBLICATION_WORKFLOW Detail")

        # StatePermissionRelation
        self.admin = permissions.utils.register_role("Admin")
        spr = StatePermissionRelation.objects.create(state=self.public, permission=self.detail, role=self.admin)
        self.assertEqual(spr.__unicode__(), "Public Admin Detail")


class WorkflowManagerTestCase(TestCase):

    def setUp(self):
        self.publication_1 = Publication.objects.create(name="Publication 1", owner=User.objects.create(username="user_1"))
        self.publication_2 = Publication.objects.create(name="Publication 2", owner=User.objects.create(username="user_2"))
        self.publication_3 = Publication.objects.create(name="Publication 3", owner=User.objects.create(username="user_3"))
        self.publication_4 = Publication.objects.create(name="Publication 4", owner=User.objects.create(username="user_4"))
        self.publication_5 = Publication.objects.create(name="Publication 5", owner=User.objects.create(username="user_5"))

    def test_managers(self):
        self.assertEqual(Publication.objects.public().count(), 0)

        self.publication_1.do_make_public(self.publication_1.owner)
        self.publication_3.do_make_public(self.publication_3.owner)
        self.publication_5.do_make_public(self.publication_5.owner)

        self.assertEqual(Publication.objects.public().count(), 3)
        self.assertEqual(Publication.objects.private().count(), 2)

        self.publication_1.do_make_private(self.publication_1.owner)
        self.publication_5.do_make_private(self.publication_5.owner)

        self.assertEqual(Publication.objects.public().count(), 1)
        self.assertEqual(Publication.objects.private().count(), 4)


# Helpers ####################################################################

def create_publication():
    return Publication.objects.create(name="Standard", owner=User.objects.create(username="john"))


# Taken from "http://www.djangosnippets.org/snippets/963/"
class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.

    Usage:

    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})

    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client

    Once you have a request object you can pass it to any view function,
    just as if that view had been hooked up using a URLconf.

    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)


def create_request():
    """
    """
    rf = RequestFactory()
    request = rf.get('/')
    request.session = SessionStore()

    user = User()
    user.is_superuser = True
    user.save()
    request.user = user

    return request
