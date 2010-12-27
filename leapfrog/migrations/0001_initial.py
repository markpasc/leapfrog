# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Account'
        db.create_table('rhino_account', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('who', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('rhino', ['Account'])

        # Adding model 'Object'
        db.create_table('rhino_object', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('foreign_id', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('foreign_id_hash', self.gf('django.db.models.fields.CharField')(max_length=40, unique=True, null=True, db_index=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('permalink_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('time', self.gf('django.db.models.fields.DateTimeField')(db_index=True)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('image_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('image_width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('image_height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='authored', null=True, to=orm['rhino.Object'])),
            ('in_reply_to', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='replies', null=True, to=orm['rhino.Object'])),
            ('object_type', self.gf('django.db.models.fields.CharField')(default='', max_length=15, blank=True)),
        ))
        db.send_create_signal('rhino', ['Object'])

        # Adding M2M table for field attachments on 'Object'
        db.create_table('rhino_object_attachments', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_object', models.ForeignKey(orm['rhino.object'], null=False)),
            ('to_object', models.ForeignKey(orm['rhino.object'], null=False))
        ))
        db.create_unique('rhino_object_attachments', ['from_object_id', 'to_object_id'])

        # Adding model 'UserStream'
        db.create_table('rhino_userstream', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('obj', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stream_items', to=orm['rhino.Object'])),
            ('who', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stream_items', to=orm['auth.User'])),
            ('when', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('rhino', ['UserStream'])

        # Adding model 'UserReplyStream'
        db.create_table('rhino_userreplystream', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('who', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reply_stream_items', to=orm['auth.User'])),
            ('root', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reply_reply_stream_items', to=orm['rhino.Object'])),
            ('root_when', self.gf('django.db.models.fields.DateTimeField')()),
            ('reply', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reply_stream_items', to=orm['rhino.Object'])),
            ('reply_when', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('rhino', ['UserReplyStream'])


    def backwards(self, orm):
        
        # Deleting model 'Account'
        db.delete_table('rhino_account')

        # Deleting model 'Object'
        db.delete_table('rhino_object')

        # Removing M2M table for field attachments on 'Object'
        db.delete_table('rhino_object_attachments')

        # Deleting model 'UserStream'
        db.delete_table('rhino_userstream')

        # Deleting model 'UserReplyStream'
        db.delete_table('rhino_userreplystream')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'rhino.account': {
            'Meta': {'object_name': 'Account'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'who': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'rhino.object': {
            'Meta': {'object_name': 'Object'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'attached_to'", 'blank': 'True', 'to': "orm['rhino.Object']"}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored'", 'null': 'True', 'to': "orm['rhino.Object']"}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'foreign_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'foreign_id_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'unique': 'True', 'null': 'True', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'image_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'image_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['rhino.Object']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'object_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '15', 'blank': 'True'}),
            'permalink_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'})
        },
        'rhino.userreplystream': {
            'Meta': {'object_name': 'UserReplyStream'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reply': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_stream_items'", 'to': "orm['rhino.Object']"}),
            'reply_when': ('django.db.models.fields.DateTimeField', [], {}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_reply_stream_items'", 'to': "orm['rhino.Object']"}),
            'root_when': ('django.db.models.fields.DateTimeField', [], {}),
            'who': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_stream_items'", 'to': "orm['auth.User']"})
        },
        'rhino.userstream': {
            'Meta': {'object_name': 'UserStream'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'obj': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['rhino.Object']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'who': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['rhino']
