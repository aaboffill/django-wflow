==========================
Django WFlow
==========================

A workflow solution for django applications, based on django-workflows core.

Changelog
=========
0.1.6
-----

Fix some details to run successfully using unit test.

0.1.5
-----

Fix - Natural keys implementation for Workflow.

0.1.4
-----

Natural keys implementation for Workflow.


0.1.0
-----

Based on django-workflows core, some common methods are added to the workflow enabled models, in order to
decrease the implementation time of each workflow. A model to save historical workflow transitions is also added.
In order to make workflow configuration easier, in this version you can configure workflows by the declaring a dict
in django settings and workflows will be automatically created.

Notes
-----

PENDING...

Usage
-----

1. Run ``python setup.py install`` to install.

2. Modify your Django settings to use ``permissions`` and ``workflows``:

3. Add the decorator ``workflow_enabled`` to the models that will have workflow behavior.
    When you run the project this decorator will add some common methods: transitions methods and the methods
    to check current workflow state. An attribute ``current_state`` will also be added.

4. Configure the workflows:
    Define a ``WORKFLOWS`` setting for each application containing a ``workflow_enabled`` model.
    This setting must be a dictionary with following format:

    - Each workflow inside the dict will be identified by the corresponding workflow enabled model path, in the
    value of that dictionary key, will be the rest of the workflow configuration.

    - The rest of the workflow configuration will be represented by:
        + name: Workflow Name
        + roles: The name of the roles related to the workflow
        + permissions: The permissions related to the workflow
        + initial_state: The workflow initial state
        + states: The rest of the workflow states
        + transitions: The workflow transitions
        + state_transitions: The allowed transitions for each state
        + user_roles: The relation between users and roles. Each user would be specified by a workflow attribute or
        some workflow method defined in the related workflow enabled model.

    Example:
    # WORKFLOWS DEFINITIONS
    WORKFLOWS = {
        'test.models.Publication': {
            'name': 'PUBLICATION_WORKFLOW',
            'roles': ['Owner', 'Closer', 'Admin'],
            'permissions': [
                {
                    'name': 'Make Private Permission',
                    'codename': 'MAKE_PRIVATE_PERM',
                },
                {
                    'name': 'Make Public Permission',
                    'codename': 'MAKE_PUBLIC_PERM',
                },
                {
                    'name': 'End Permission',
                    'codename': 'END_PERM',
                }
            ],
            'initial_state': {
                'name': 'Private State',
                # StatePermissionRelation
                'state_perm_relation': [
                    {
                        'role': 'Owner',
                        'permission': 'MAKE_PUBLIC_PERM',
                    },
                    {
                        'role': 'Admin',
                        'permission': 'MAKE_PUBLIC_PERM',
                    },
                    {
                        'role': 'Admin',
                        'permission': 'END_PERM',
                    },
                    {
                        'role': 'Closer',
                        'permission': 'END_PERM',
                    }
                ]
            },
            'states': [
                {
                    'name': 'Public State',
                    # StatePermissionRelation
                    'state_perm_relation': [
                        {
                            'role': 'Owner',
                            'permission': 'MAKE_PRIVATE_PERM',
                        },
                        {
                            'role': 'Admin',
                            'permission': 'MAKE_PRIVATE_PERM',
                        },
                        {
                            'role': 'Admin',
                            'permission': 'END_PERM',
                        },
                        {
                            'role': 'Closer',
                            'permission': 'END_PERM',
                        }
                    ]
                },
                {
                    'name': 'End State',
                    # StatePermissionRelation
                    'state_perm_relation': []
                },
            ],
            'transitions': [
                {
                    'name': 'Make Public Transition',
                    'destination': 'Public State',
                    'permission': 'MAKE_PUBLIC_PERM',
                    'description': 'Make Public Transition',
                },
                {
                    'name': 'Make Private Transition',
                    'destination': 'Private State',
                    'permission': 'MAKE_PRIVATE_PERM',
                    'description': 'Make Private Transition',
                },
                {
                    'name': 'End Transition',
                    'destination': 'End State',
                    'permission': 'END_PERM',
                    'description': 'End Transition',
                    'condition': 'condition_transition',
                },
            ],
            'state_transitions': {
                'Private State': ['Make Public Transition', 'End Transition'],
                'Public State': ['Make Private Transition', 'End Transition'],
            },
            'user_roles': [
                # for each item will try to find the user value as an attribute or method of the related workflow model
                # you can specify attributes of the attributes
                {
                    'user_path': 'owner',
                    'role': 'Owner'
                },
                {
                    'user_path': 'item.creator',
                    'role': 'Closer'
                },
                {
                    'user_path': 'administrators',
                    'role': 'Admin'
                }
            ]
        }
    }

5. Add the workflow setting to the project settings.
    Example:
    # APPLICATION WORKFLOWS
    workflows = getattr(settings, 'WORKFLOWS', {})
    workflows.update(WORKFLOWS)
    setattr(settings, 'WORKFLOWS', workflows)