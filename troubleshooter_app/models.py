from django.db import models

class TroubleshooterGuide(models.Model):
    """
    A simple model to represent a troubleshooting guide.
    This is the "Model" part of the MVT pattern, defining the data structure.
    
    This model is provided as an example. You can adapt it or replace it
    with your own models as needed for your application.
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    solution = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        # A simple ordering for the guides.
        ordering = ['-created_at']