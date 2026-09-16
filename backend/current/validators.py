import zipfile
from pathlib import Path

from rest_framework import serializers


MAX_UPLOAD_SIZE = 25 * 1024 * 1024
OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


def _prepare(uploaded_file, extensions):
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in extensions:
        raise serializers.ValidationError(f"仅支持 {', '.join(sorted(extensions))} 文件。")
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        raise serializers.ValidationError("文件大小不能超过 25 MB。")
    uploaded_file.seek(0)
    return extension


def validate_pdf_upload(uploaded_file):
    _prepare(uploaded_file, {".pdf"})
    has_header = uploaded_file.read(5) == b"%PDF-"
    uploaded_file.seek(max(0, uploaded_file.size - 1024))
    has_eof = b"%%EOF" in uploaded_file.read()
    if not has_header or not has_eof:
        uploaded_file.seek(0)
        raise serializers.ValidationError("文件内容不是有效的 PDF。")
    uploaded_file.seek(0)
    return uploaded_file


def validate_word_upload(uploaded_file):
    extension = _prepare(uploaded_file, {".doc", ".docx"})
    if extension == ".doc":
        valid = uploaded_file.read(8) == OLE_SIGNATURE
    else:
        try:
            with zipfile.ZipFile(uploaded_file) as archive:
                names = set(archive.namelist())
                valid = "[Content_Types].xml" in names and any(name.startswith("word/") for name in names)
        except (zipfile.BadZipFile, OSError):
            valid = False
    uploaded_file.seek(0)
    if not valid:
        raise serializers.ValidationError("文件内容不是有效的 Word 文档。")
    return uploaded_file
