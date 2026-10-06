from django.contrib import admin

from .models import RequestUpdate, ServiceRequest


class RequestUpdateInline(admin.TabularInline):
    model = RequestUpdate
    extra = 0
    readonly_fields = ['created_at']


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = [
        'reference',
        'subject',
        'request_type',
        'priority',
        'status',
        'requester',
        'assigned_to',
        'submitted_at',
    ]
    list_filter = ['status', 'priority', 'request_type', 'department']
    search_fields = ['reference', 'subject', 'description', 'requester__username']
    readonly_fields = ['reference', 'submitted_at', 'updated_at']
    inlines = [RequestUpdateInline]


@admin.register(RequestUpdate)
class RequestUpdateAdmin(admin.ModelAdmin):
    list_display = ['request', 'author', 'previous_status', 'new_status', 'created_at']
    list_filter = ['previous_status', 'new_status', 'created_at']
    search_fields = ['request__subject', 'comment', 'author__username']
    readonly_fields = ['created_at']
