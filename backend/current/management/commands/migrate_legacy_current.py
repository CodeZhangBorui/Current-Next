import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from django.contrib.auth.models import Permission
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone as django_timezone

from current.models import AuditLog, Entry, EntryFileVersion, EntryStateEvent, ImportRun, Issue, SiteConfig, User


class Command(BaseCommand):
    help = "Import the archived Flask SQLite databases and uploads into Current."

    def add_arguments(self, parser):
        parser.add_argument("--orion-db", required=True, type=Path)
        parser.add_argument("--current-db", required=True, type=Path)
        parser.add_argument("--uploads-root", required=True, type=Path)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--report", type=Path)

    def handle(self, *args, **options):
        orion_db = options["orion_db"]
        current_db = options["current_db"]
        uploads_root = options["uploads_root"]
        dry_run = options["dry_run"]
        report_path = options["report"]

        for source in (orion_db, current_db):
            if not source.exists():
                raise CommandError(f"Source database does not exist: {source}")
        if not uploads_root.exists():
            raise CommandError(f"Uploads directory does not exist: {uploads_root}")

        report = self.inspect(orion_db, current_db, uploads_root)
        report["mode"] = "dry-run" if dry_run else "import"
        report["source_fingerprint"] = self.fingerprint(orion_db, current_db)
        if report_path:
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run complete; no application data was changed."))
            return
        if report["errors"]:
            raise CommandError("Import stopped because source validation found errors. Use --dry-run and fix the report first.")

        with transaction.atomic():
            self.import_all(orion_db, current_db, uploads_root, report)
        self.stdout.write(self.style.SUCCESS("Legacy import completed successfully."))

    def connect(self, path):
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return connection

    def table_exists(self, connection, table):
        return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def inspect(self, orion_path, current_path, uploads_root):
        report = {"counts": {}, "ignored_tables": ["sessions", "sudo"], "files": {"referenced": 0, "missing": [], "orphaned": []}, "errors": [], "warnings": []}
        with closing(self.connect(orion_path)) as orion, closing(self.connect(current_path)) as current:
            for connection, tables in ((orion, ("users", "sessions", "permissions", "configuration", "auditlog")), (current, ("issues", "entries", "sudo"))):
                for table in tables:
                    report["counts"][table] = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] if self.table_exists(connection, table) else 0
            issue_ids = {row[0] for row in current.execute("SELECT id FROM issues").fetchall()} if self.table_exists(current, "issues") else set()
            for row in current.execute("SELECT uuid, issue_id FROM entries").fetchall() if self.table_exists(current, "entries") else []:
                if row[1] not in issue_ids:
                    report["errors"].append(f"entry {row[0]} references missing issue {row[1]}")
                self.check_file(uploads_root / str(row[0]), report)
            for issue_id in issue_ids:
                issue_file = uploads_root / "issues" / f"{issue_id}.pdf"
                if issue_file.exists():
                    report["files"]["referenced"] += 1
                else:
                    report["warnings"].append(f"published PDF is missing for issue {issue_id}")
        referenced_paths = {str((uploads_root / str(path)).resolve()) for path in self.referenced_upload_names(current_path)}
        referenced_paths.update(str((uploads_root / "issues" / path).resolve()) for path in self.referenced_issue_files(current_path))
        for file_path in uploads_root.rglob("*"):
            if file_path.is_file() and str(file_path.resolve()) not in referenced_paths:
                report["files"]["orphaned"].append(str(file_path.relative_to(uploads_root)))
        return report

    def check_file(self, path, report):
        if path.exists():
            report["files"]["referenced"] += 1
        else:
            report["files"]["missing"].append(str(path))

    def referenced_upload_names(self, current_path):
        with closing(self.connect(current_path)) as connection:
            if not self.table_exists(connection, "entries"):
                return []
            return [row[0] for row in connection.execute("SELECT uuid FROM entries").fetchall()]

    def referenced_issue_files(self, current_path):
        with closing(self.connect(current_path)) as connection:
            if not self.table_exists(connection, "issues"):
                return []
            return [f"{row[0]}.pdf" for row in connection.execute("SELECT id FROM issues").fetchall()]

    def fingerprint(self, *paths):
        digest = hashlib.sha256()
        for path in paths:
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def import_all(self, orion_path, current_path, uploads_root, report):
        with closing(self.connect(orion_path)) as orion, closing(self.connect(current_path)) as current:
            self.import_users(orion)
            self.import_permissions(orion)
            self.import_configuration(orion)
            self.import_audit(orion)
            self.import_issues(current, uploads_root, report)
            self.import_entries(current, uploads_root)
            ImportRun.objects.create(mode="import", source_fingerprint=report["source_fingerprint"], completed_at=django_timezone.now(), report=report)

    def import_users(self, connection):
        if not self.table_exists(connection, "users"):
            return
        columns = [column[1] for column in connection.execute("PRAGMA table_info(users)").fetchall()]
        for row in connection.execute("SELECT * FROM users").fetchall():
            values = dict(zip(columns, row))
            user = User.objects.filter(username=values["name"]).first()
            created = user is None
            if created:
                source_id = values.get("id")
                create_values = {"id": source_id} if source_id and not User.objects.filter(pk=source_id).exists() else {}
                user = User.objects.create(username=values["name"], **create_values)
            user.grade = int(values.get("grade") or 0)
            user.classnum = int(values.get("classnum") or 0)
            user.is_active = str(values.get("active", "1")).lower() not in ("0", "false", "no")
            user.legacy_password_hash = values.get("passwd", "") or ""
            if created:
                user.set_unusable_password()
            user.save(update_fields=["grade", "classnum", "is_active", "legacy_password_hash", "password"] if created else ["grade", "classnum", "is_active", "legacy_password_hash"])

    def import_permissions(self, connection):
        permission_map = {permission.codename: permission for permission in Permission.objects.filter(content_type__app_label="current")}
        if "create_entry" in permission_map:
            for user in User.objects.all():
                user.user_permissions.add(permission_map["create_entry"])
        if not self.table_exists(connection, "permissions"):
            return
        rows = connection.execute("SELECT target, node FROM permissions").fetchall()
        nodes_by_target = {}
        for target, node in rows:
            nodes_by_target.setdefault(target, set()).add(node)
        for user in User.objects.all():
            direct_nodes = nodes_by_target.get(user.username, set())
            nodes = set(direct_nodes)
            for group_name in (node for node in direct_nodes if node.startswith("group.")):
                nodes.update(nodes_by_target.get(group_name, set()))
            permission_names = {"create_entry"}
            if "entries.review.*" in nodes:
                permission_names.add("review_entry")
            if "entries.select.*" in nodes:
                permission_names.add("select_entry")
            if "*" in nodes or "management" in nodes:
                permission_names.update(permission_map)
                user.is_staff = True
                user.save(update_fields=["is_staff"])
            user.user_permissions.add(*(permission_map[name] for name in permission_names if name in permission_map))

    def import_configuration(self, connection):
        if not self.table_exists(connection, "configuration"):
            return
        SiteConfig.objects.all().delete()
        for row in connection.execute("SELECT key, value, type FROM configuration").fetchall():
            SiteConfig.objects.update_or_create(key=row[0], defaults={"value": row[1] or "", "value_type": row[2] or "str"})

    def import_audit(self, connection):
        if not self.table_exists(connection, "auditlog"):
            return
        AuditLog.objects.all().delete()
        for row in connection.execute("SELECT time, scope, executer, message FROM auditlog").fetchall():
            AuditLog.objects.create(timestamp=datetime.fromtimestamp(row[0], tz=timezone.utc), scope=row[1], executor=row[2] or "", message=row[3] or "")

    def import_issues(self, connection, uploads_root, report):
        if not self.table_exists(connection, "issues"):
            return
        for row in connection.execute("SELECT id, date, subject2, subject3, subject4, leader, editors, respeditor, ispublished FROM issues").fetchall():
            leader_name = (row[5] or "").strip()
            responsible_editor_name = (row[7] or "").strip()
            leader = User.objects.filter(username=leader_name).first() if leader_name else None
            responsible_editor = User.objects.filter(username=responsible_editor_name).first() if responsible_editor_name else None
            if leader_name and leader is None:
                report["warnings"].append(f"issue {row[0]} leader not found: {leader_name}")
            if responsible_editor_name and responsible_editor is None:
                report["warnings"].append(f"issue {row[0]} responsible editor not found: {responsible_editor_name}")
            defaults = {"deadline": datetime.fromtimestamp(row[1], tz=timezone.utc), "subject2": row[2] or "", "subject3": row[3] or "", "subject4": row[4] or "", "leader": leader, "responsible_editor": responsible_editor, "published": bool(row[8])}
            issue = Issue.objects.update_or_create(issue_number=row[0], defaults=defaults)[0]
            editor_names = [item.strip() for item in (row[6] or "").split(",") if item.strip()]
            missing_editors = [name for name in editor_names if not User.objects.filter(username=name).exists()]
            report["warnings"].extend(f"issue {row[0]} editor not found: {name}" for name in missing_editors)
            issue.editors.set(User.objects.filter(username__in=editor_names))
            pdf_path = uploads_root / "issues" / f"{issue.issue_number}.pdf"
            if pdf_path.exists() and not issue.pdf:
                with pdf_path.open("rb") as source:
                    issue.pdf.save(pdf_path.name, File(source), save=True)

    def import_entries(self, connection, uploads_root):
        if not self.table_exists(connection, "entries"):
            return
        for row in connection.execute("SELECT uuid, issue_id, filename, page, title, origin, wordcount, description, selector, reviewer, status FROM entries").fetchall():
            selector_name = (row[8] or "").strip()
            reviewer_name = (row[9] or "").strip()
            entry_status = row[10] if row[10] in dict(Entry.Status.choices) else Entry.Status.PENDING
            submitter = User.objects.filter(username=selector_name).first() if selector_name else None
            reviewer = User.objects.filter(username=reviewer_name).first() if reviewer_name else None
            defaults = {"issue_id": row[1], "filename": row[2] or "", "page": row[3], "title": row[4] or "", "origin": row[5] or "", "wordcount": row[6] or 0, "description": row[7] or "", "submitter": submitter, "selector_name": selector_name, "reviewer_name": reviewer_name, "status": entry_status}
            if entry_status in (Entry.Status.REVIEWED, Entry.Status.SELECTED):
                defaults.update({"review_completed_by": reviewer, "review_completed_at": django_timezone.now()})
            if entry_status == Entry.Status.SELECTED:
                defaults.update({"closed_from_status": Entry.Status.REVIEWED, "merged_at": django_timezone.now()})
            entry = Entry.objects.update_or_create(uuid=row[0], defaults=defaults)[0]
            source_path = uploads_root / str(entry.uuid)
            if source_path.exists() and not entry.file:
                with source_path.open("rb") as source:
                    entry.file.save(entry.filename or source_path.name, File(source), save=True)
            if entry.file:
                EntryFileVersion.objects.get_or_create(
                    entry=entry,
                    version=1,
                    defaults={"filename": entry.filename or Path(entry.file.name).name, "file": entry.file.name, "uploader": reviewer or submitter, "uploader_name": reviewer_name or selector_name, "source": EntryFileVersion.Source.LEGACY, "note": "从 Current 数据库导入"},
                )
            if entry_status in (Entry.Status.REVIEWED, Entry.Status.SELECTED):
                EntryStateEvent.objects.get_or_create(
                    entry=entry,
                    action=EntryStateEvent.Action.REVIEW_COMPLETED,
                    defaults={"actor": reviewer, "actor_name": reviewer_name, "from_status": Entry.Status.CREATED, "to_status": Entry.Status.REVIEWED, "note": "从 Current 数据库导入"},
                )
            if entry_status == Entry.Status.SELECTED:
                EntryStateEvent.objects.get_or_create(
                    entry=entry,
                    action=EntryStateEvent.Action.CLOSED_MERGED,
                    defaults={"from_status": Entry.Status.REVIEWED, "to_status": Entry.Status.SELECTED, "note": "从 Current 已选录状态导入"},
                )
