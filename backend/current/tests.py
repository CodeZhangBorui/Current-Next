import hashlib
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from django.core.management import call_command
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client
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

            User.objects.create(pk=7, username="existing-user")
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

    def test_issue_api_uses_user_objects_for_people_fields(self):
        creator = User.objects.create_user(username="creator", password="secret")
        leader = User.objects.create_user(username="leader", password="secret")
        editor = User.objects.create_user(username="editor", password="secret")
        responsible = User.objects.create_user(username="responsible", password="secret")
        permission = Permission.objects.get(codename="create_issue")
        creator.user_permissions.add(permission)
        self.client.force_login(creator)

        response = self.client.post(
            "/api/v1/issues",
            {
                "id": 12,
                "deadline": "2030-01-02T10:00:00Z",
                "subject": ["校园", "文化", "体育"],
                "leader_id": leader.pk,
                "editor_ids": [editor.pk],
                "responsible_editor_id": responsible.pk,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["leader"], {"id": leader.pk, "username": "leader", "grade": 0, "classnum": 0, "is_active": True, "is_staff": False})
        self.assertEqual(data["editors"][0]["username"], "editor")
        self.assertEqual(data["responsible_editor"]["username"], "responsible")

    def test_local_next_origin_is_allowed_for_csrf_protected_post(self):
        creator = User.objects.create_user(username="csrf-creator", password="secret")
        creator.user_permissions.add(Permission.objects.get(codename="create_issue"))
        client = Client(enforce_csrf_checks=True)
        client.force_login(creator)

        csrf_response = client.get("/api/v1/auth/csrf", HTTP_ORIGIN="http://localhost:3000")
        token = csrf_response.cookies["csrftoken"].value
        response = client.post(
            "/api/v1/issues",
            {"id": 99, "deadline": "2030-01-02T10:00:00Z", "subject": ["校园", "文化", "体育"]},
            content_type="application/json",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 201)

    def test_staff_member_can_save_and_publish_announcement(self):
        administrator = User.objects.create_user(username="announcement-admin", password="secret", is_staff=True)
        member = User.objects.create_user(username="announcement-member", password="secret")

        self.client.force_login(member)
        self.assertEqual(self.client.get("/api/v1/announcement/manage").status_code, 403)

        self.client.force_login(administrator)
        draft = self.client.post(
            "/api/v1/announcement/manage",
            {"action": "save", "content": "明天中午截止收稿。"},
            content_type="application/json",
        )
        self.assertEqual(draft.status_code, 200)
        self.assertEqual(draft.json()["draft"], "明天中午截止收稿。")
        self.assertEqual(self.client.get("/api/v1/announcement").json()["content"], "")

        published = self.client.post(
            "/api/v1/announcement/manage",
            {"action": "publish", "content": "本期征稿将于明天中午截止。"},
            content_type="application/json",
        )
        self.assertEqual(published.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/announcement").json()["content"], "本期征稿将于明天中午截止。")
