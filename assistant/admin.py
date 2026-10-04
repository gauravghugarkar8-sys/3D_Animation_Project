from django.contrib import admin

from .models import ConversationSession, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "intent", "created_at")
    can_delete = False


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("session_key", "user_label", "last_topic", "created_at", "updated_at")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "intent", "created_at")
    list_filter = ("role", "intent")
    search_fields = ("content",)
