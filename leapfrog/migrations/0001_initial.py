# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Media'
        db.create_table('leapfrog_media', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('image_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('embed_code', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('leapfrog', ['Media'])

        # Adding model 'Person'
        db.create_table('leapfrog_person', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, null=True, blank=True)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('avatar', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['leapfrog.Media'], null=True, blank=True)),
            ('permalink_url', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('leapfrog', ['Person'])

        # Adding model 'Account'
        db.create_table('leapfrog_account', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('ident', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2000, 1, 1, 0, 0))),
            ('authinfo', self.gf('django.db.models.fields.CharField')(max_length=600, blank=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounts', to=orm['leapfrog.Person'])),
            ('status_background_color', self.gf('django.db.models.fields.CharField')(max_length=6, blank=True)),
            ('status_background_image_url', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('status_background_tile', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('leapfrog', ['Account'])

        # Adding unique constraint on 'Account', fields ['service', 'ident']
        db.create_unique('leapfrog_account', ['service', 'ident'])

        # Adding model 'Object'
        db.create_table('leapfrog_object', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
            ('foreign_id', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('body', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='represented_objects', null=True, to=orm['leapfrog.Media'])),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='authored_objects', null=True, to=orm['leapfrog.Account'])),
            ('render_mode', self.gf('django.db.models.fields.CharField')(default='', max_length=15, blank=True)),
            ('time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow, db_index=True)),
            ('permalink_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('in_reply_to', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='replies', null=True, to=orm['leapfrog.Object'])),
        ))
        db.send_create_signal('leapfrog', ['Object'])

        # Adding unique constraint on 'Object', fields ['service', 'foreign_id']
        db.create_unique('leapfrog_object', ['service', 'foreign_id'])

        # Adding model 'UserStream'
        db.create_table('leapfrog_userstream', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('obj', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stream_items', to=orm['leapfrog.Object'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stream_items', to=orm['auth.User'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.utcnow)),
            ('why_account', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stream_items_caused', to=orm['leapfrog.Account'])),
            ('why_verb', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal('leapfrog', ['UserStream'])

        # Adding unique constraint on 'UserStream', fields ['user', 'obj']
        db.create_unique('leapfrog_userstream', ['user_id', 'obj_id'])

        # Adding model 'UserReplyStream'
        db.create_table('leapfrog_userreplystream', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reply_stream_items', to=orm['auth.User'])),
            ('root', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reply_reply_stream_items', to=orm['leapfrog.Object'])),
            ('root_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('reply', self.gf('django.db.models.fields.related.ForeignKey')(related_name='reply_stream_items', to=orm['leapfrog.Object'])),
            ('reply_time', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('leapfrog', ['UserReplyStream'])

        # Adding unique constraint on 'UserReplyStream', fields ['user', 'reply']
        db.create_unique('leapfrog_userreplystream', ['user_id', 'reply_id'])

        # Adding model 'UserSetting'
        db.create_table('leapfrog_usersetting', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=250)),
        ))
        db.send_create_signal('leapfrog', ['UserSetting'])

        # Adding unique constraint on 'UserSetting', fields ['user', 'key']
        db.create_unique('leapfrog_usersetting', ['user_id', 'key'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'UserSetting', fields ['user', 'key']
        db.delete_unique('leapfrog_usersetting', ['user_id', 'key'])

        # Removing unique constraint on 'UserReplyStream', fields ['user', 'reply']
        db.delete_unique('leapfrog_userreplystream', ['user_id', 'reply_id'])

        # Removing unique constraint on 'UserStream', fields ['user', 'obj']
        db.delete_unique('leapfrog_userstream', ['user_id', 'obj_id'])

        # Removing unique constraint on 'Object', fields ['service', 'foreign_id']
        db.delete_unique('leapfrog_object', ['service', 'foreign_id'])

        # Removing unique constraint on 'Account', fields ['service', 'ident']
        db.delete_unique('leapfrog_account', ['service', 'ident'])

        # Deleting model 'Media'
        db.delete_table('leapfrog_media')

        # Deleting model 'Person'
        db.delete_table('leapfrog_person')

        # Deleting model 'Account'
        db.delete_table('leapfrog_account')

        # Deleting model 'Object'
        db.delete_table('leapfrog_object')

        # Deleting model 'UserStream'
        db.delete_table('leapfrog_userstream')

        # Deleting model 'UserReplyStream'
        db.delete_table('leapfrog_userreplystream')

        # Deleting model 'UserSetting'
        db.delete_table('leapfrog_usersetting')


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
        'leapfrog.account': {
            'Meta': {'unique_together': "(('service', 'ident'),)", 'object_name': 'Account'},
            'authinfo': ('django.db.models.fields.CharField', [], {'max_length': '600', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2000, 1, 1, 0, 0)'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accounts'", 'to': "orm['leapfrog.Person']"}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'status_background_color': ('django.db.models.fields.CharField', [], {'max_length': '6', 'blank': 'True'}),
            'status_background_image_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'status_background_tile': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'leapfrog.media': {
            'Meta': {'object_name': 'Media'},
            'embed_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'leapfrog.object': {
            'Meta': {'unique_together': "(('service', 'foreign_id'),)", 'object_name': 'Object'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored_objects'", 'null': 'True', 'to': "orm['leapfrog.Account']"}),
            'body': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'foreign_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'represented_objects'", 'null': 'True', 'to': "orm['leapfrog.Media']"}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['leapfrog.Object']"}),
            'permalink_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'render_mode': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '15', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'leapfrog.person': {
            'Meta': {'object_name': 'Person'},
            'avatar': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['leapfrog.Media']", 'null': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permalink_url': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'leapfrog.userreplystream': {
            'Meta': {'unique_together': "(('user', 'reply'),)", 'object_name': 'UserReplyStream'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reply': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_stream_items'", 'to': "orm['leapfrog.Object']"}),
            'reply_time': ('django.db.models.fields.DateTimeField', [], {}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_reply_stream_items'", 'to': "orm['leapfrog.Object']"}),
            'root_time': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_stream_items'", 'to': "orm['auth.User']"})
        },
        'leapfrog.usersetting': {
            'Meta': {'unique_together': "(('user', 'key'),)", 'object_name': 'UserSetting'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        },
        'leapfrog.userstream': {
            'Meta': {'unique_together': "(('user', 'obj'),)", 'object_name': 'UserStream'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'obj': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['leapfrog.Object']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.utcnow'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['auth.User']"}),
            'why_account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items_caused'", 'to': "orm['leapfrog.Account']"}),
            'why_verb': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['leapfrog']
