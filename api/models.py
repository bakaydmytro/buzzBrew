from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    access_token = models.CharField(max_length=255, default='')
    instagram_user_id = models.CharField(max_length=50, default='')

#TODO check if needed
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = slugify(self.email.split('@')[0])
        super().save(*args, **kwargs)

class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=100)

class Job(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='jobs')