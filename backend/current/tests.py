import hashlib
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client
from django.test import TestCase
from django.utils import timezone

from .models import Entry, EntryFileVersion, EntryStateEvent, Issue, User


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
                db.executemany("INSERT INTO permissions VALUES (?, ?)", (("student", "clients.login"), ("student", "group.default"), ("group.default", "entries.review.*")))
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
            self.assertEqual(Entry.objects.get(pk="entry-1").versions.count(), 1)
            self.assertEqual(Entry.objects.get(pk="entry-1").versions.get().source, EntryFileVersion.Source.LEGACY)
            self.assertTrue(user.groups.filter(name="Current Editors").exists())
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

    def test_entry_api_accepts_multipart_upload(self):
        contributor = User.objects.create_user(username="contributor", password="secret")
        contributor.user_permissions.add(Permission.objects.get(codename="create_entry"))
        Issue.objects.create(issue_number=88, deadline=timezone.now())
        self.client.force_login(contributor)

        response = self.client.post(
            "/api/v1/issues/88/entries",
            {
                "page": "1",
                "title": "投稿标题",
                "origin": "校园记者站",
                "wordcount": "120",
                "description": "投稿简介",
                "file": SimpleUploadedFile("article.docx", b"document-content"),
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["filename"], "article.docx")
        self.assertEqual(Entry.objects.get(pk=response.json()["uuid"]).versions.count(), 1)

    def test_pull_request_style_entry_review_workflow(self):
        submitter = User.objects.create_user(username="submitter", password="secret")
        reviewer = User.objects.create_user(username="reviewer", password="secret")
        chief = User.objects.create_user(username="chief", password="secret")
        outsider = User.objects.create_user(username="outsider", password="secret")
        submitter.user_permissions.add(Permission.objects.get(codename="create_entry"))
        issue = Issue.objects.create(issue_number=89, deadline=timezone.now(), responsible_editor=chief)
        issue.editors.add(reviewer)

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.client.force_login(submitter)
            created = self.client.post(
                "/api/v1/issues/89/entries",
                {
                    "page": "2",
                    "title": "版本化稿件",
                    "origin": "校园记者站",
                    "wordcount": "240",
                    "description": "用于审核流程测试",
                    "file": SimpleUploadedFile("draft-v1.docx", b"version-one"),
                },
            )
            self.assertEqual(created.status_code, 201)
            entry_uuid = created.json()["uuid"]

            self.client.force_login(chief)
            chief_open_detail = self.client.get(f"/api/v1/entries/{entry_uuid}/review")
            self.assertTrue(chief_open_detail.json()["capabilities"]["can_close"])
            closed_invalid = self.client.post(
                f"/api/v1/entries/{entry_uuid}/close",
                {"disposition": "invalid", "note": "稿件方向不符合本期主题"},
                content_type="application/json",
            )
            self.assertEqual(closed_invalid.status_code, 200)
            self.assertEqual(closed_invalid.json()["status"], Entry.Status.INVALID)
            reopened_invalid = self.client.post(
                f"/api/v1/entries/{entry_uuid}/reopen",
                {"note": "重新评估后恢复审核"},
                content_type="application/json",
            )
            self.assertEqual(reopened_invalid.status_code, 200)
            self.assertEqual(reopened_invalid.json()["status"], Entry.Status.CREATED)

            self.client.force_login(outsider)
            denied = self.client.post(f"/api/v1/entries/{entry_uuid}/comments", {"body": "不应被接受"}, content_type="application/json")
            self.assertEqual(denied.status_code, 403)

            self.client.force_login(reviewer)
            detail = self.client.get(f"/api/v1/entries/{entry_uuid}/review")
            self.assertTrue(detail.json()["capabilities"]["can_upload_version"])
            comment = self.client.post(f"/api/v1/entries/{entry_uuid}/comments", {"body": "请调整标题。"}, content_type="application/json")
            self.assertEqual(comment.status_code, 201)
            uploaded = self.client.post(
                f"/api/v1/entries/{entry_uuid}/versions",
                {"note": "已调整标题", "file": SimpleUploadedFile("draft-v2.docx", b"version-two")},
            )
            self.assertEqual(uploaded.status_code, 201)
            self.assertEqual([version["version"] for version in uploaded.json()["versions"]], [1, 2])
            completed = self.client.post(f"/api/v1/entries/{entry_uuid}/complete-review", {}, content_type="application/json")
            self.assertEqual(completed.status_code, 200)
            self.assertEqual(completed.json()["status"], Entry.Status.REVIEWED)
            locked_upload = self.client.post(
                f"/api/v1/entries/{entry_uuid}/versions",
                {"file": SimpleUploadedFile("draft-v3.docx", b"version-three")},
            )
            self.assertEqual(locked_upload.status_code, 400)

            self.client.force_login(outsider)
            denied_return = self.client.post(
                f"/api/v1/entries/{entry_uuid}/return-to-review",
                {"note": "无权退回"},
                content_type="application/json",
            )
            self.assertEqual(denied_return.status_code, 403)

            self.client.force_login(chief)
            chief_detail = self.client.get(f"/api/v1/entries/{entry_uuid}/review")
            self.assertTrue(chief_detail.json()["capabilities"]["can_merge"])
            self.assertTrue(chief_detail.json()["capabilities"]["can_return_to_review"])
            returned = self.client.post(
                f"/api/v1/entries/{entry_uuid}/return-to-review",
                {"note": "标题仍需调整"},
                content_type="application/json",
            )
            self.assertEqual(returned.status_code, 200)
            self.assertEqual(returned.json()["status"], Entry.Status.CREATED)
            self.assertIsNone(returned.json()["review_completed_by"])
            self.assertIsNone(returned.json()["review_completed_at"])
            self.assertEqual(len(returned.json()["versions"]), 2)

            self.client.force_login(reviewer)
            uploaded_again = self.client.post(
                f"/api/v1/entries/{entry_uuid}/versions",
                {"note": "按终审意见调整", "file": SimpleUploadedFile("draft-v3.docx", b"version-three")},
            )
            self.assertEqual(uploaded_again.status_code, 201)
            self.assertEqual([version["version"] for version in uploaded_again.json()["versions"]], [1, 2, 3])
            completed_again = self.client.post(f"/api/v1/entries/{entry_uuid}/complete-review", {}, content_type="application/json")
            self.assertEqual(completed_again.status_code, 200)
            self.assertEqual(completed_again.json()["status"], Entry.Status.REVIEWED)

            self.client.force_login(chief)
            chief_comment = self.client.post(f"/api/v1/entries/{entry_uuid}/comments", {"body": "终审通过。"}, content_type="application/json")
            self.assertEqual(chief_comment.status_code, 201)
            merged = self.client.post(f"/api/v1/entries/{entry_uuid}/merge", {}, content_type="application/json")
            self.assertEqual(merged.status_code, 200)
            self.assertEqual(merged.json()["status"], Entry.Status.SELECTED)
            self.assertEqual(merged.json()["merged_by"]["username"], "chief")
            self.assertEqual(len(merged.json()["comments"]), 2)
            reopened_merged = self.client.post(
                f"/api/v1/entries/{entry_uuid}/reopen",
                {"note": "需要补充终审说明"},
                content_type="application/json",
            )
            self.assertEqual(reopened_merged.status_code, 200)
            self.assertEqual(reopened_merged.json()["status"], Entry.Status.REVIEWED)
            self.assertIsNone(reopened_merged.json()["merged_by"])

            entry = Entry.objects.get(pk=entry_uuid)
            self.assertEqual(entry.versions.count(), 3)
            self.assertEqual(entry.filename, "draft-v3.docx")
            self.assertEqual(
                list(entry.state_events.values_list("action", flat=True)),
                [
                    EntryStateEvent.Action.CLOSED_INVALID,
                    EntryStateEvent.Action.REOPENED,
                    EntryStateEvent.Action.REVIEW_COMPLETED,
                    EntryStateEvent.Action.REVIEW_RETURNED,
                    EntryStateEvent.Action.REVIEW_COMPLETED,
                    EntryStateEvent.Action.CLOSED_MERGED,
                    EntryStateEvent.Action.REOPENED,
                ],
            )
