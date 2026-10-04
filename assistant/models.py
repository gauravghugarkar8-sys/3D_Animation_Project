from django.db import models


class ConversationSession(models.Model):
    """One live MindMesh session, tied to a Django browser session."""

    session_key = models.CharField(max_length=64, unique=True)
    user_label = models.CharField(max_length=120, blank=True, default="")
    last_topic = models.CharField(
        max_length=120, blank=True, default="",
        help_text="Most recent 'tell me about X' topic, for follow-up "
                   "questions like 'what about the brain?' or 'tell me more'.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Session {self.session_key[:8]} ({self.created_at:%Y-%m-%d %H:%M})"


class Message(models.Model):
    """A single turn in the conversation — either the user or MindMesh."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    session = models.ForeignKey(
        ConversationSession, related_name="messages", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=40, blank=True, default="")
    visual_type = models.CharField(max_length=40, blank=True, default="")
    visual_payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        preview = self.content[:40]
        return f"[{self.role}] {preview}"
