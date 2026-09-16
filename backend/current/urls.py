from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf", views.csrf),
    path("auth/login", views.login_view),
    path("auth/me", views.me),
    path("auth/logout", views.logout_view),
    path("auth/password", views.change_password),
    path("issues", views.issues),
    path("statistics", views.statistics),
    path("users/choices", views.user_choices),
    path("issues/<int:issue_number>", views.issue_detail),
    path("issues/<int:issue_number>/pdf/upload", views.upload_issue_pdf),
    path("issues/<int:issue_number>/publish", views.publish_issue),
    path("issues/<int:issue_number>/unpublish", views.unpublish_issue),
    path("issues/<int:issue_number>/pdf", views.issue_pdf),
    path("issues/<int:issue_number>/entries", views.entries),
    path("entries/<str:entry_uuid>/review", views.entry_review_detail),
    path("entries/<str:entry_uuid>/versions", views.upload_entry_version),
    path("entries/<str:entry_uuid>/versions/<int:version_number>/file", views.entry_version_file),
    path("entries/<str:entry_uuid>/comments", views.add_entry_comment),
    path("entries/<str:entry_uuid>/complete-review", views.complete_entry_review),
    path("entries/<str:entry_uuid>/return-to-review", views.return_entry_to_review),
    path("entries/<str:entry_uuid>/close", views.close_entry),
    path("entries/<str:entry_uuid>/merge", views.merge_entry),
    path("entries/<str:entry_uuid>/reopen", views.reopen_entry),
    path("entries/<str:entry_uuid>", views.remove_entry),
    path("entries/<str:entry_uuid>/file", views.entry_file),
    path("announcement", views.announcement),
    path("announcement/manage", views.manage_announcement),
]
