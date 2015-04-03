# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Workflow'
        db.create_table(u'workflows_workflow', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('initial_state', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='workflow_state', null=True, to=orm['workflows.State'])),
        ))
        db.send_create_signal(u'workflows', ['Workflow'])

        # Adding model 'State'
        db.create_table(u'workflows_state', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('workflow', self.gf('django.db.models.fields.related.ForeignKey')(related_name='states', to=orm['workflows.Workflow'])),
        ))
        db.send_create_signal(u'workflows', ['State'])

        # Adding M2M table for field transitions on 'State'
        m2m_table_name = db.shorten_name(u'workflows_state_transitions')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('state', models.ForeignKey(orm[u'workflows.state'], null=False)),
            ('transition', models.ForeignKey(orm[u'workflows.transition'], null=False))
        ))
        db.create_unique(m2m_table_name, ['state_id', 'transition_id'])

        # Adding model 'Transition'
        db.create_table(u'workflows_transition', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('workflow', self.gf('django.db.models.fields.related.ForeignKey')(related_name='transitions', to=orm['workflows.Workflow'])),
            ('destination', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='destination_state', null=True, to=orm['workflows.State'])),
            ('condition', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('permission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['permissions.Permission'], null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=1000, null=True, blank=True)),
        ))
        db.send_create_signal(u'workflows', ['Transition'])

        # Adding model 'StateObjectRelation'
        db.create_table(u'workflows_stateobjectrelation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='state_object', null=True, to=orm['contenttypes.ContentType'])),
            ('content_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['workflows.State'])),
        ))
        db.send_create_signal(u'workflows', ['StateObjectRelation'])

        # Adding unique constraint on 'StateObjectRelation', fields ['content_type', 'content_id', 'state']
        db.create_unique(u'workflows_stateobjectrelation', ['content_type_id', 'content_id', 'state_id'])

        # Adding model 'WorkflowObjectRelation'
        db.create_table(u'workflows_workflowobjectrelation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='workflow_object', null=True, to=orm['contenttypes.ContentType'])),
            ('content_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('workflow', self.gf('django.db.models.fields.related.ForeignKey')(related_name='wors', to=orm['workflows.Workflow'])),
        ))
        db.send_create_signal(u'workflows', ['WorkflowObjectRelation'])

        # Adding unique constraint on 'WorkflowObjectRelation', fields ['content_type', 'content_id']
        db.create_unique(u'workflows_workflowobjectrelation', ['content_type_id', 'content_id'])

        # Adding model 'WorkflowModelRelation'
        db.create_table(u'workflows_workflowmodelrelation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], unique=True)),
            ('workflow', self.gf('django.db.models.fields.related.ForeignKey')(related_name='wmrs', to=orm['workflows.Workflow'])),
        ))
        db.send_create_signal(u'workflows', ['WorkflowModelRelation'])

        # Adding model 'WorkflowPermissionRelation'
        db.create_table(u'workflows_workflowpermissionrelation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('workflow', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['workflows.Workflow'])),
            ('permission', self.gf('django.db.models.fields.related.ForeignKey')(related_name='permissions', to=orm['permissions.Permission'])),
        ))
        db.send_create_signal(u'workflows', ['WorkflowPermissionRelation'])

        # Adding unique constraint on 'WorkflowPermissionRelation', fields ['workflow', 'permission']
        db.create_unique(u'workflows_workflowpermissionrelation', ['workflow_id', 'permission_id'])

        # Adding model 'StateInheritanceBlock'
        db.create_table(u'workflows_stateinheritanceblock', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['workflows.State'])),
            ('permission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['permissions.Permission'])),
        ))
        db.send_create_signal(u'workflows', ['StateInheritanceBlock'])

        # Adding model 'StatePermissionRelation'
        db.create_table(u'workflows_statepermissionrelation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['workflows.State'])),
            ('permission', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['permissions.Permission'])),
            ('role', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['permissions.Role'])),
        ))
        db.send_create_signal(u'workflows', ['StatePermissionRelation'])

        # Adding model 'WorkflowHistorical'
        db.create_table(u'workflows_workflowhistorical', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='content_type_set_for_workflowhistorical', to=orm['contenttypes.ContentType'])),
            ('content_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['workflows.State'])),
            ('transition', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['workflows.Transition'], null=True, blank=True)),
            ('update_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'workflows', ['WorkflowHistorical'])


    def backwards(self, orm):
        # Removing unique constraint on 'WorkflowPermissionRelation', fields ['workflow', 'permission']
        db.delete_unique(u'workflows_workflowpermissionrelation', ['workflow_id', 'permission_id'])

        # Removing unique constraint on 'WorkflowObjectRelation', fields ['content_type', 'content_id']
        db.delete_unique(u'workflows_workflowobjectrelation', ['content_type_id', 'content_id'])

        # Removing unique constraint on 'StateObjectRelation', fields ['content_type', 'content_id', 'state']
        db.delete_unique(u'workflows_stateobjectrelation', ['content_type_id', 'content_id', 'state_id'])

        # Deleting model 'Workflow'
        db.delete_table(u'workflows_workflow')

        # Deleting model 'State'
        db.delete_table(u'workflows_state')

        # Removing M2M table for field transitions on 'State'
        db.delete_table(db.shorten_name(u'workflows_state_transitions'))

        # Deleting model 'Transition'
        db.delete_table(u'workflows_transition')

        # Deleting model 'StateObjectRelation'
        db.delete_table(u'workflows_stateobjectrelation')

        # Deleting model 'WorkflowObjectRelation'
        db.delete_table(u'workflows_workflowobjectrelation')

        # Deleting model 'WorkflowModelRelation'
        db.delete_table(u'workflows_workflowmodelrelation')

        # Deleting model 'WorkflowPermissionRelation'
        db.delete_table(u'workflows_workflowpermissionrelation')

        # Deleting model 'StateInheritanceBlock'
        db.delete_table(u'workflows_stateinheritanceblock')

        # Deleting model 'StatePermissionRelation'
        db.delete_table(u'workflows_statepermissionrelation')

        # Deleting model 'WorkflowHistorical'
        db.delete_table(u'workflows_workflowhistorical')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'permissions.permission': {
            'Meta': {'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'content_types': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'content_types'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'permissions.role': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Role'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'workflows.state': {
            'Meta': {'ordering': "('name',)", 'object_name': 'State'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'transitions': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'states'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['workflows.Transition']"}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'states'", 'to': u"orm['workflows.Workflow']"})
        },
        u'workflows.stateinheritanceblock': {
            'Meta': {'object_name': 'StateInheritanceBlock'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['permissions.Permission']"}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['workflows.State']"})
        },
        u'workflows.stateobjectrelation': {
            'Meta': {'unique_together': "(('content_type', 'content_id', 'state'),)", 'object_name': 'StateObjectRelation'},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'state_object'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['workflows.State']"})
        },
        u'workflows.statepermissionrelation': {
            'Meta': {'object_name': 'StatePermissionRelation'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['permissions.Permission']"}),
            'role': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['permissions.Role']"}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['workflows.State']"})
        },
        u'workflows.transition': {
            'Meta': {'object_name': 'Transition'},
            'condition': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'destination_state'", 'null': 'True', 'to': u"orm['workflows.State']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['permissions.Permission']", 'null': 'True', 'blank': 'True'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'transitions'", 'to': u"orm['workflows.Workflow']"})
        },
        u'workflows.workflow': {
            'Meta': {'object_name': 'Workflow'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial_state': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_state'", 'null': 'True', 'to': u"orm['workflows.State']"}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['permissions.Permission']", 'through': u"orm['workflows.WorkflowPermissionRelation']", 'symmetrical': 'False'})
        },
        u'workflows.workflowhistorical': {
            'Meta': {'object_name': 'WorkflowHistorical'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'content_type_set_for_workflowhistorical'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['workflows.State']"}),
            'transition': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['workflows.Transition']", 'null': 'True', 'blank': 'True'}),
            'update_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'workflows.workflowmodelrelation': {
            'Meta': {'object_name': 'WorkflowModelRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wmrs'", 'to': u"orm['workflows.Workflow']"})
        },
        u'workflows.workflowobjectrelation': {
            'Meta': {'unique_together': "(('content_type', 'content_id'),)", 'object_name': 'WorkflowObjectRelation'},
            'content_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'workflow_object'", 'null': 'True', 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'wors'", 'to': u"orm['workflows.Workflow']"})
        },
        u'workflows.workflowpermissionrelation': {
            'Meta': {'unique_together': "(('workflow', 'permission'),)", 'object_name': 'WorkflowPermissionRelation'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permission': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'permissions'", 'to': u"orm['permissions.Permission']"}),
            'workflow': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['workflows.Workflow']"})
        }
    }

    complete_apps = ['workflows']