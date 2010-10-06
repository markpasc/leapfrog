# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Media'
        db.create_table('rhino_media', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('image_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('embed_code', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('rhino', ['Media'])

        # Deleting field 'Object.foreign_id_hash'
        db.delete_column('rhino_object', 'foreign_id_hash')

        # Deleting field 'Object.image_width'
        db.delete_column('rhino_object', 'image_width')

        # Deleting field 'Object.image_height'
        db.delete_column('rhino_object', 'image_height')

        # Deleting field 'Object.image_url'
        db.delete_column('rhino_object', 'image_url')

        # Adding field 'Object.service'
        db.add_column('rhino_object', 'service', self.gf('django.db.models.fields.CharField')(default='', max_length=20, blank=True), keep_default=False)

        # Adding field 'Object.media'
        db.add_column('rhino_object', 'media', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rhino.Media'], null=True), keep_default=False)

        # Changing field 'Object.foreign_id'
        db.alter_column('rhino_object', 'foreign_id', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Deleting field 'UserStream.who'
        db.delete_column('rhino_userstream', 'who_id')

        # Adding field 'UserStream.author'
        db.add_column('rhino_userstream', 'author', self.gf('django.db.models.fields.related.ForeignKey')(default='THIS SHOULD HAVE BEEN WHO', related_name='stream_items', to=orm['auth.User']), keep_default=False)

        # Adding field 'UserStream.why_who'
        db.add_column('rhino_userstream', 'why_who', self.gf('django.db.models.fields.related.ForeignKey')(default='hi', related_name='stream_items_caused', to=orm['auth.User']), keep_default=False)

        # Adding field 'UserStream.why_verb'
        db.add_column('rhino_userstream', 'why_verb', self.gf('django.db.models.fields.CharField')(default='muh', max_length=20), keep_default=False)


    def backwards(self, orm):
        
        # Deleting model 'Media'
        db.delete_table('rhino_media')

        # Adding field 'Object.foreign_id_hash'
        db.add_column('rhino_object', 'foreign_id_hash', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40, null=True, db_index=True), keep_default=False)

        # Adding field 'Object.image_width'
        db.add_column('rhino_object', 'image_width', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True), keep_default=False)

        # Adding field 'Object.image_height'
        db.add_column('rhino_object', 'image_height', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True), keep_default=False)

        # Adding field 'Object.image_url'
        db.add_column('rhino_object', 'image_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True), keep_default=False)

        # Deleting field 'Object.service'
        db.delete_column('rhino_object', 'service')

        # Deleting field 'Object.media'
        db.delete_column('rhino_object', 'media_id')

        # Changing field 'Object.foreign_id'
        db.alter_column('rhino_object', 'foreign_id', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # We cannot add back in field 'UserStream.who'
        raise RuntimeError(
            "Cannot reverse this migration. 'UserStream.who' and its values cannot be restored.")

        # Deleting field 'UserStream.author'
        db.delete_column('rhino_userstream', 'author_id')

        # Deleting field 'UserStream.why_who'
        db.delete_column('rhino_userstream', 'why_who_id')

        # Deleting field 'UserStream.why_verb'
        db.delete_column('rhino_userstream', 'why_verb')


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
            'authinfo': ('django.db.models.fields.CharField', [], {'max_length': '600', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'who': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'rhino.media': {
            'Meta': {'object_name': 'Media'},
            'embed_code': ('django.db.models.fields.TextField', [], {}),
            'height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'rhino.object': {
            'Meta': {'object_name': 'Object'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'attached_to'", 'blank': 'True', 'to': "orm['rhino.Object']"}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored'", 'null': 'True', 'to': "orm['rhino.Object']"}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'foreign_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['rhino.Object']"}),
            'media': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['rhino.Media']", 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'object_type': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '15', 'blank': 'True'}),
            'permalink_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
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
            'author': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'obj': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['rhino.Object']"}),
            'when': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'why_verb': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'why_who': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items_caused'", 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['rhino']
