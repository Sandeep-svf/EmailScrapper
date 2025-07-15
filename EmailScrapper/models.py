# app/models.py

from django.db import models
from django.utils import timezone

class EmailScrapeJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    url = models.URLField()
    emails = models.TextField(blank=True)  # comma-separated emails
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_urls = models.PositiveIntegerField(default=0)
    completed_urls = models.PositiveIntegerField(default=0)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ScrapeJob #{self.pk} - {self.status}"
