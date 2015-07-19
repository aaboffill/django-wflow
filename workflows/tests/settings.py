# coding=utf-8

DEBUG = True

SITE_ID = 1

SECRET_KEY = 'blabla'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    }
}

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'permissions',
    'workflows',
    'workflows.tests'
]

# WORKFLOWS DEFINITIONS
WORKFLOWS = {
    'workflows.tests.models.Publication': {
        'name': 'PUBLICATION_WORKFLOW',
        'roles': ['Anonymous', 'Owner'],
        'permissions': [
            {
                'name': 'View',
                'codename': 'view',
            },
            {
                'name': 'Edit',
                'codename': 'edit',
            },
        ],
        'initial_state': {
            'name': 'Private',
            # StatePermissionRelation
            'state_perm_relation': [
                {
                    'role': 'Owner',
                    'permission': 'view',
                },
                {
                    'role': 'Owner',
                    'permission': 'edit',
                },
            ]
        },
        'states': [
            {
                'name': 'Public',
                # StatePermissionRelation
                'state_perm_relation': [
                    {
                        'role': 'Owner',
                        'permission': 'view',
                    },
                ]
            },
        ],
        'transitions': [
            {
                'name': 'Make public',
                'destination': 'Public',
                'permission': 'edit',
                'description': 'Make Public Transition',
                'condition': 'another_make_public_check',
            },
            {
                'name': 'Make private',
                'destination': 'Private',
                'permission': 'view',
                'description': 'Make Private Transition',
                'condition': 'another_make_private_check',
            },
        ],
        'state_transitions': {
            'Private': ['Make public'],
            'Public': ['Make private'],
        },
        'user_roles': [
            # for each item will try to find the user value as an attribute or method of the related workflow model
            # you can specify attributes of the attributes
            {
                'user_path': 'owner',
                'role': 'Owner'
            },
        ]
    }
}
