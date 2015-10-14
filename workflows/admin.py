# coding=utf-8
from django.contrib import admin
from .models import State
from .models import StateInheritanceBlock
from .models import StatePermissionRelation
from .models import StateObjectRelation
from .models import Transition
from .models import Workflow
from .models import WorkflowObjectRelation
from .models import WorkflowModelRelation
from .models import WorkflowPermissionRelation


class StateInline(admin.TabularInline):
    model = State

class WorkflowAdmin(admin.ModelAdmin):
    inlines = [
        StateInline,
    ]

admin.site.register(Workflow, WorkflowAdmin)

admin.site.register(State)
admin.site.register(StateInheritanceBlock)
admin.site.register(StateObjectRelation)
admin.site.register(StatePermissionRelation)
admin.site.register(Transition)
admin.site.register(WorkflowObjectRelation)
admin.site.register(WorkflowModelRelation)
admin.site.register(WorkflowPermissionRelation)

