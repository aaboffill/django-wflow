# coding=utf-8
from django.contrib.auth.models import User
from django.db import models
from workflows.decorators import workflow_enabled


@workflow_enabled
class Publication(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User)


