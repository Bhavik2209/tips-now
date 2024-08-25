from django.db import models
from django.utils import timezone

class Tip(models.Model):
    username = models.CharField(max_length=100)
    twitter_username = models.CharField(max_length=100, blank=True)
    content = models.TextField()
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.username}: {self.content[:50]}..."