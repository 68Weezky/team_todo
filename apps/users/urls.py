"""
URL patterns for the users app.
"""
from django.contrib.auth.views import PasswordResetCompleteView, PasswordResetDoneView
from django.urls import path

from . import notification_views, task_views, team_views, views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    
    # Password reset
    path('password-reset/', 
         views.TeamTodoPasswordResetView.as_view(), 
         name='password_reset'),
    path('password-reset/done/', 
         PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/',
         views.TeamTodoPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),
    
    # User management
    path('users/', views.user_list, name='user_list'),
    
    # Dashboards
    path('dashboard/', task_views.dashboard_redirect, name='dashboard'),
    path('dashboard/leader/', task_views.leader_dashboard, name='dashboard_leader'),
    path('dashboard/member/', task_views.member_dashboard, name='dashboard_member'),

    # Team management
    path('teams/', team_views.team_list, name='team_list'),
    path('teams/create/', team_views.team_create, name='team_create'),
    path('teams/<int:pk>/', team_views.team_detail, name='team_detail'),
    path('teams/<int:pk>/edit/', team_views.team_edit, name='team_edit'),
    path('teams/<int:pk>/delete/', team_views.team_delete, name='team_delete'),
    path('teams/<int:pk>/members/', team_views.manage_members, name='manage_members'),
    path('teams/<int:pk>/remove-member/<int:user_id>/', team_views.remove_member, name='remove_member'),
    path('teams/<int:pk>/leave/', team_views.leave_team, name='leave_team'),
    
    # Task management
    path('teams/<int:team_id>/tasks/', task_views.task_list, name='task_list'),
    path('teams/<int:team_id>/tasks/create/', task_views.task_create, name='task_create'),
    path('teams/<int:team_id>/tasks/<int:task_id>/', task_views.task_detail, name='task_detail'),
    path('teams/<int:team_id>/tasks/<int:task_id>/edit/', task_views.task_edit, name='task_edit'),
    path('teams/<int:team_id>/tasks/<int:task_id>/delete/', task_views.task_delete, name='task_delete'),
    path('teams/<int:team_id>/tasks/<int:task_id>/status/', task_views.task_update_status, name='task_update_status'),
    path('teams/<int:team_id>/tasks/<int:task_id>/comment/', task_views.task_add_comment, name='task_add_comment'),
    path('teams/<int:team_id>/tasks/<int:task_id>/attach/', task_views.task_upload_attachment, name='task_upload_attachment'),
    path('my-tasks/', task_views.my_tasks, name='my_tasks'),

    # Analytics & reporting
    path('analytics/team/<int:team_id>/', task_views.team_analytics, name='team_analytics'),
    path('analytics/personal/', task_views.personal_stats, name='personal_stats'),
    path('reports/export-csv/', task_views.export_tasks_csv, name='export_tasks_csv'),
    path('reports/export-personal-pdf/', task_views.export_personal_tasks_pdf, name='export_personal_tasks_pdf'),

    # Notifications
    path('notifications/', notification_views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/mark-read/', notification_views.mark_notification_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', notification_views.mark_all_notifications_read, name='notification_mark_all_read'),

    # Global search
    path('search/', task_views.search, name='search'),
]
