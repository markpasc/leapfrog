# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Person'
        db.create_table('rhino_person', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('rhino', ['Person'])

        # Deleting field 'Account.who'
        db.delete_column('rhino_account', 'who_id')

        # Adding field 'Account.user'
        db.add_column('rhino_account', 'user', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['auth.User']), keep_default=False)

        # Adding field 'Account.person'
        db.add_column('rhino_account', 'person', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='accounts', to=orm['rhino.Person']), keep_default=False)

        # Deleting field 'UserStream.author'
        db.delete_column('rhino_userstream', 'author_id')

        # Deleting field 'UserStream.why_who'
        db.delete_column('rhino_userstream', 'why_who_id')

        # Deleting field 'UserStream.when'
        db.delete_column('rhino_userstream', 'when')

        # Adding field 'UserStream.user'
        db.add_column('rhino_userstream', 'user', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='stream_items', to=orm['auth.User']), keep_default=False)

        # Adding field 'UserStream.time'
        db.add_column('rhino_userstream', 'time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=0, blank=True), keep_default=False)

        # Adding field 'UserStream.why_account'
        db.add_column('rhino_userstream', 'why_account', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='stream_items_caused', to=orm['rhino.Account']), keep_default=False)

        # Deleting field 'UserReplyStream.who'
        db.delete_column('rhino_userreplystream', 'who_id')

        # Deleting field 'UserReplyStream.reply_when'
        db.delete_column('rhino_userreplystream', 'reply_when')

        # Deleting field 'UserReplyStream.root_when'
        db.delete_column('rhino_userreplystream', 'root_when')

        # Adding field 'UserReplyStream.user'
        db.add_column('rhino_userreplystream', 'user', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='reply_stream_items', to=orm['auth.User']), keep_default=False)

        # Adding field 'UserReplyStream.root_time'
        db.add_column('rhino_userreplystream', 'root_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 10, 6)), keep_default=False)

        # Adding field 'UserReplyStream.reply_time'
        db.add_column('rhino_userreplystream', 'reply_time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 10, 6)), keep_default=False)

        # Adding field 'Object.author'
        db.add_column('rhino_object', 'author', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='authored_objects', null=True, to=orm['rhino.Account']), keep_default=False)


    def backwards(self, orm):
        
        # Deleting model 'Person'
        db.delete_table('rhino_person')

        # Adding field 'Account.who'
        db.add_column('rhino_account', 'who', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['auth.User']), keep_default=False)

        # Deleting field 'Account.user'
        db.delete_column('rhino_account', 'user_id')

        # Deleting field 'Account.person'
        db.delete_column('rhino_account', 'person_id')

        # Adding field 'UserStream.author'
        db.add_column('rhino_userstream', 'author', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='stream_items', to=orm['auth.User']), keep_default=False)

        # Adding field 'UserStream.why_who'
        db.add_column('rhino_userstream', 'why_who', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='stream_items_caused', to=orm['auth.User']), keep_default=False)

        # Adding field 'UserStream.when'
        db.add_column('rhino_userstream', 'when', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=datetime.date(2010, 10, 6), blank=True), keep_default=False)

        # Deleting field 'UserStream.user'
        db.delete_column('rhino_userstream', 'user_id')

        # Deleting field 'UserStream.time'
        db.delete_column('rhino_userstream', 'time')

        # Deleting field 'UserStream.why_account'
        db.delete_column('rhino_userstream', 'why_account_id')

        # Adding field 'UserReplyStream.who'
        db.add_column('rhino_userreplystream', 'who', self.gf('django.db.models.fields.related.ForeignKey')(default=0, related_name='reply_stream_items', to=orm['auth.User']), keep_default=False)

        # Adding field 'UserReplyStream.reply_when'
        db.add_column('rhino_userreplystream', 'reply_when', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 10, 6)), keep_default=False)

        # Adding field 'UserReplyStream.root_when'
        db.add_column('rhino_userreplystream', 'root_when', self.gf('django.db.models.fields.DateTimeField')(default=datetime.date(2010, 10, 6)), keep_default=False)

        # Deleting field 'UserReplyStream.user'
        db.delete_column('rhino_userreplystream', 'user_id')

        # Deleting field 'UserReplyStream.root_time'
        db.delete_column('rhino_userreplystream', 'root_time')

        # Deleting field 'UserReplyStream.reply_time'
        db.delete_column('rhino_userreplystream', 'reply_time')

        # Deleting field 'Object.author'
        db.delete_column('rhino_object', 'author_id')


    models = {
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
        },
        'rhino.account': {
            'Meta': {'object_name': 'Account'},
            'authinfo': ('django.db.models.fields.CharField', [], {'max_length': '600', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ident': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accounts'", 'to': "orm['rhino.Person']"}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
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
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored_objects'", 'null': 'True', 'to': "orm['rhino.Account']"}),
            'body': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'foreign_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'represented_objects'", 'null': 'True', 'to': "orm['rhino.Media']"}),
            'in_reply_to': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'replies'", 'null': 'True', 'to': "orm['rhino.Object']"}),
            'permalink_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'render_mode': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '15', 'blank': 'True'}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        },
        'rhino.person': {
            'Meta': {'object_name': 'Person'},
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'rhino.userreplystream': {
            'Meta': {'object_name': 'UserReplyStream'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reply': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_stream_items'", 'to': "orm['rhino.Object']"}),
            'reply_time': ('django.db.models.fields.DateTimeField', [], {}),
            'root': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_reply_stream_items'", 'to': "orm['rhino.Object']"}),
            'root_time': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'reply_stream_items'", 'to': "orm['auth.User']"})
        },
        'rhino.userstream': {
            'Meta': {'object_name': 'UserStream'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'obj': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['rhino.Object']"}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items'", 'to': "orm['auth.User']"}),
            'why_account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stream_items_caused'", 'to': "orm['rhino.Account']"}),
            'why_verb': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        }
    }

    complete_apps = ['rhino']
