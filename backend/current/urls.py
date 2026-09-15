from django.urls import path

from . import views

urlpatterns = [
    path("auth/csrf", views.csrf),
    path("auth/login", views.login_view),
    path("auth/me", views.me),
    path("auth/logout", views.logout_view),
    path("auth/password", views.change_password),
    path("issues", views.issues),
    path("issues/<int:issue_number>", views.issue_detail),
    path("issues/<int:issue_number>/publish", views.publish_issue),
    path("issues/<int:issue_number>/pdf", views.issue_pdf),
    path("issues/<int:issue_number>/entries", views.entries),
    path("entries/<str:entry_uuid>/review", views.review_entry),
    path("entries/<str:entry_uuid>/select", views.select_entry),
    path("entries/<str:entry_uuid>", views.remove_entry),
    path("entries/<str:entry_uuid>/file", views.entry_file),
    path("announcement", views.announcement),
]
