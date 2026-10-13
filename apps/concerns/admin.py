from django.contrib import admin

from .models import (
    ConcernCategory,
    ConcernReport,
    GeographicArea,
    ReportAssignmentHistory,
    ReportAttachment,
    ReportStatusHistory,
)


@admin.register(GeographicArea)
class GeographicAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'parent', 'code', 'is_active']
    list_filter = ['level', 'is_active']
    search_fields = ['name', 'code']


@admin.register(ConcernCategory)
class ConcernCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'sort_order', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'description']


class ReportStatusHistoryInline(admin.TabularInline):
    model = ReportStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = [
        'actor', 'old_status', 'new_status', 'comment', 'visibility', 'created_at',
    ]

    def has_add_permission(self, request, obj=None):
        return False


class ReportAssignmentHistoryInline(admin.TabularInline):
    model = ReportAssignmentHistory
    extra = 0
    can_delete = False
    readonly_fields = [
        'department', 'assignee', 'assigned_by', 'note', 'assigned_at', 'ended_at',
    ]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ConcernReport)
class ConcernReportAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'subject', 'category', 'area', 'priority',
        'status', 'department', 'assigned_to', 'submitted_at',
    ]
    list_filter = ['status', 'priority', 'category', 'area', 'department']
    search_fields = ['reference', 'subject', 'description', 'location_details']
    readonly_fields = [
        field.name for field in ConcernReport._meta.fields
    ]
    inlines = [
        ReportStatusHistoryInline,
        ReportAssignmentHistoryInline,
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReportStatusHistory)
class ReportStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['report', 'actor', 'old_status', 'new_status', 'visibility', 'created_at']
    list_filter = ['visibility', 'old_status', 'new_status']
    search_fields = ['report__subject', 'comment', 'actor__username']
    readonly_fields = [field.name for field in ReportStatusHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReportAssignmentHistory)
class ReportAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ['report', 'department', 'assignee', 'assigned_by', 'assigned_at', 'ended_at']
    list_filter = ['department', 'assigned_at']
    search_fields = ['report__subject', 'assignee__username']
    readonly_fields = [field.name for field in ReportAssignmentHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReportAttachment)
class ReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ['report', 'original_name', 'content_type', 'size_bytes', 'uploaded_at']
    search_fields = ['report__subject', 'original_name']
    readonly_fields = [field.name for field in ReportAttachment._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
