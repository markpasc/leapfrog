# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Object.time'
        db.add_column('aggregator_object', 'time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2010, 9, 21, 0, 5, 43, 519376), db_index=True), keep_default=False)

        # Adding field 'Object.author'
        db.add_column('aggregator_object', 'author', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='authored', null=True, to=orm['aggregator.Object']), keep_default=False)

        # Changing field 'Object.image_width'
        db.alter_column('aggregator_object', 'image_width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True))

        # Changing field 'Object.image_height'
        db.alter_column('aggregator_object', 'image_height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True))

        # Changing field 'Object.in_reply_to'
        db.alter_column('aggregator_object', 'in_reply_to_id', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, null=True, to=orm['aggregator.Object']))

        # Changing field 'Subscription.topic_url_hash'
        db.alter_column('aggregator_subscription', 'topic_url_hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40, blank=True))

        # Changing field 'Activity.target'
        db.alter_column('aggregator_activity', 'target_id', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, null=True, to=orm['aggregator.Object']))

        # Changing field 'Activity.object'
        db.alter_column('aggregator_activity', 'object_id', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, null=True, to=orm['aggregator.Object']))

        # Changing field 'Activity.actor'
        db.alter_column('aggregator_activity', 'actor_id', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, null=True, to=orm['aggregator.Object']))


    def backwards(self, orm):
        
        # Deleting field 'Object.time'
        db.delete_column('aggregator_object', 'time')

        # Deleting field 'Object.author'
        db.delete_column('aggregator_object', 'author_id')

        # Changing field 'Object.image_width'
        db.alter_column('aggregator_object', 'image_width', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Object.image_height'
        db.alter_column('aggregator_object', 'image_height', self.gf('django.db.models.fields.IntegerField')(null=True))

        # Changing field 'Object.in_reply_to'
        db.alter_column('aggregator_object', 'in_reply_to_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['aggregator.Object'], null=True))

        # Changing field 'Subscription.topic_url_hash'
        db.alter_column('aggregator_subscription', 'topic_url_hash', self.gf('django.db.models.fields.CharField')(max_length=40, unique=True))

        # Changing field 'Activity.target'
        db.alter_column('aggregator_activity', 'target_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['aggregator.Object']))

        # Changing field 'Activity.object'
        db.alter_column('aggregator_activity', 'object_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['aggregator.Object']))

        # Changing field 'Activity.actor'
        db.alter_column('aggregator_activity', 'actor_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['aggregator.Object']))


    models = {
        'aggregator.activity': {
            'Meta': {'object_name': 'Activity'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activities_with_actor'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activities_with_object'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activities'", 'to': "orm['aggregator.Subscription']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activities_with_target'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'uniq_hash': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '40', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activities'", 'null': 'True', 'to': "orm['auth.User']"}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'aggregator.object': {
            'Meta': {'object_name': 'Object'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'attached_to'", 'blank': 'True', 'to': "orm['aggregator.Object']"}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'foreign_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'foreign_id_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'unique': 'True', 'null': 'True', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'image_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['aggregator.Object']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'object_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '15', 'blank': 'True'}),
            'permalink_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        'aggregator.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mode': ('django.db.models.fields.CharField', [], {'default': "'poll'", 'max_length': '20'}),
            'topic_url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'topic_url_hash': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'unique': 'True', 'max_length': '40', 'blank': 'True'}),
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
