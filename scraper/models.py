# scraper/models.py

from django.db import models

class EmailScrapeBatch(models.Model):
    name = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='pending')  # pending, in_progress, completed
    file_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class EmailScrapeJob(models.Model):
    batch = models.ForeignKey(EmailScrapeBatch, related_name='jobs', on_delete=models.CASCADE)
    url = models.URLField()
    status = models.CharField(max_length=20, default='pending')  # pending, completed, failed
    emails = models.TextField(blank=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    total_urls = models.PositiveIntegerField(default=0)
    completed_urls = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.url} ({self.status})"

