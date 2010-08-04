# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Subscription'
        db.create_table('aggregator_subscription', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=75, null=True, blank=True)),
            ('topic_url', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('topic_url_hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40, db_index=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='aggregator_subscriptions', null=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('aggregator', ['Subscription'])

        # Adding model 'Object'
        db.create_table('aggregator_object', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('foreign_id', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('foreign_id_hash', self.gf('django.db.models.fields.CharField')(max_length=40, unique=True, null=True, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('permalink_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('image_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('image_width', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('image_height', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('in_reply_to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['aggregator.Object'], null=True)),
            ('object_type', self.gf('django.db.models.fields.CharField')(max_length=15)),
        ))
        db.send_create_signal('aggregator', ['Object'])

        # Adding M2M table for field attachments on 'Object'
        db.create_table('aggregator_object_attachments', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_object', models.ForeignKey(orm['aggregator.object'], null=False)),
            ('to_object', models.ForeignKey(orm['aggregator.object'], null=False))
        ))
        db.create_unique('aggregator_object_attachments', ['from_object_id', 'to_object_id'])

        # Adding model 'Activity'
        db.create_table('aggregator_activity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('verb', self.gf('django.db.models.fields.CharField')(max_length=15)),
            ('actor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activities_with_actor', null=True, to=orm['aggregator.Object'])),
            ('object', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activities_with_object', null=True, to=orm['aggregator.Object'])),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activities_with_target', null=True, to=orm['aggregator.Object'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('subscription', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activities', to=orm['aggregator.Subscription'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='activities', null=True, to=orm['auth.User'])),
            ('uniq_hash', self.gf('django.db.models.fields.CharField')(db_index=True, unique=True, max_length=40, blank=True)),
        ))
        db.send_create_signal('aggregator', ['Activity'])


    def backwards(self, orm):
        
        # Deleting model 'Subscription'
        db.delete_table('aggregator_subscription')

        # Deleting model 'Object'
        db.delete_table('aggregator_object')

        # Removing M2M table for field attachments on 'Object'
        db.delete_table('aggregator_object_attachments')

        # Deleting model 'Activity'
        db.delete_table('aggregator_activity')


    models = {
        'aggregator.activity': {
            'Meta': {'object_name': 'Activity'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activities_with_actor'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activities_with_object'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activities'", 'to': "orm['aggregator.Subscription']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activities_with_target'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'uniq_hash': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '40', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activities'", 'null': 'True', 'to': "orm['auth.User']"}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'aggregator.object': {
            'Meta': {'object_name': 'Object'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'attached_to'", 'symmetrical': 'False', 'to': "orm['aggregator.Object']"}),
            'foreign_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'foreign_id_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'unique': 'True', 'null': 'True', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_height': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'image_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'image_width': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['aggregator.Object']", 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'object_type': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'permalink_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'aggregator.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'topic_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'topic_url_hash': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'aggregator_subscriptions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['aggregator']
