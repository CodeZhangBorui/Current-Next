import hashlib
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from .models import Entry, Issue, User


class LegacyImportTests(TestCase):
    def test_legacy_import_preserves_users_business_rows_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            orion_db = root / "orion.db"
            current_db = root / "current.db"
            uploads = root / "uploads"
            (uploads / "issues").mkdir(parents=True)
            (uploads / "entry-1").write_bytes(b"docx-data")
            (uploads / "issues" / "1.pdf").write_bytes(b"pdf-data")

            with closing(sqlite3.connect(orion_db)) as db:
                db.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, passwd TEXT, grade TEXT, classnum TEXT, active TEXT); CREATE TABLE permissions (target TEXT, node TEXT); CREATE TABLE configuration (key TEXT PRIMARY KEY, value TEXT, type TEXT, defaultval TEXT); CREATE TABLE auditlog (time INTEGER, scope TEXT, executer TEXT, message TEXT);")
                db.execute("INSERT INTO users VALUES (7, 'student', ?, '10', '2', '0')", (hashlib.sha256(b"secret").hexdigest(),))
                db.execute("INSERT INTO permissions VALUES ('student', 'clients.login')")
                db.execute("INSERT INTO configuration VALUES ('site.announcement', 'hello', 'str', 'hello')")
                db.execute("INSERT INTO auditlog VALUES (1700000000, 'test', 'student', 'created')")
                db.commit()
            with closing(sqlite3.connect(current_db)) as db:
                db.executescript("CREATE TABLE issues (id INTEGER PRIMARY KEY, date INTEGER, subject2 TEXT, subject3 TEXT, subject4 TEXT, leader TEXT, editors TEXT, respeditor TEXT, ispublished INTEGER); CREATE TABLE entries (uuid TEXT PRIMARY KEY, issue_id INTEGER, filename TEXT, page INTEGER, title TEXT, origin TEXT, wordcount INTEGER, description TEXT, selector TEXT, reviewer TEXT, status TEXT); CREATE TABLE sudo (token TEXT, user TEXT, activitytime INTEGER);")
                db.execute("INSERT INTO issues VALUES (1, 1700000000, 'A', 'B', 'C', '', 'student', '', 1)")
                db.execute("INSERT INTO entries VALUES ('entry-1', 1, 'article.docx', 2, 'Title', 'School', 12, 'Description', 'student', '', 'created')")
                db.commit()

            call_command("migrate_legacy_current", orion_db=orion_db, current_db=current_db, uploads_root=uploads)

            user = User.objects.get(username="student")
            self.assertEqual(user.legacy_password_hash, hashlib.sha256(b"secret").hexdigest())
            self.assertFalse(user.is_active)
            response = self.client.post("/api/v1/auth/login", {"username": "student", "password": "secret"}, content_type="application/json")
            self.assertEqual(response.status_code, 401)
            self.assertEqual(Issue.objects.get(pk=1).subject3, "B")
            self.assertEqual(Entry.objects.get(pk="entry-1").filename, "article.docx")
            self.assertTrue(Issue.objects.get(pk=1).pdf)
            self.assertTrue(Entry.objects.get(pk="entry-1").file)
            tables = set(connection.introspection.table_names())
            self.assertNotIn("current_legacysession", tables)
            self.assertNotIn("current_legacysudo", tables)
            self.assertNotIn("current_legacypermission", tables)
