from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

import os
import random
import string

class NabraUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class NabraUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    GENDER_CHOICES = [  ('M', 'Male'),
                        ('F', 'Female'),
                        ('O', 'Other'),
                        ]
    gender = models.CharField( max_length=1, choices=GENDER_CHOICES, default='O',)
    birthday = models.DateField()
    score = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    country = models.CharField(max_length=50)

    objects = NabraUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def calculate_average_score(self):
        user_scores = self.user_scores.all()
        if user_scores.exists():
            total_score = sum(user_score.total_score_percentage() for user_score in user_scores)
            average_score = total_score / user_scores.count()
            self.score = average_score
            self.save()
        else:
            self.score = 0
            self.save()

    class Meta:
        db_table = "nabrauser"

class UserScore(models.Model):
    surah_num = models.IntegerField()
    aya_num = models.IntegerField()
    nabra_user = models.ForeignKey(NabraUser, on_delete=models.CASCADE, related_name='user_scores')
    aya_text_score = models.FloatField(default=0)
    Idgham_score = models.FloatField(default=0)
    Ikhfaa_score = models.FloatField(default=0)
    imala_score = models.FloatField(default=0)
    madd_2_score = models.FloatField(default=0)
    madd_6_Lazim_score = models.FloatField(default=0)
    madd_6_score = models.FloatField(default=0)
    madd_246_score = models.FloatField(default=0)
    qalqala_score = models.FloatField(default=0)
    tafkhim_score = models.FloatField(default=0)

    def total_score_percentage(self):
        score_fields = [
            self.aya_text_score,
            self.Idgham_score,
            self.Ikhfaa_score,
            self.imala_score,
            self.madd_2_score,
            self.madd_6_Lazim_score,
            self.madd_6_score,
            self.madd_246_score,
            self.qalqala_score,
            self.tafkhim_score
        ]
        total_score = sum(score_fields)
        return total_score / len(score_fields) if score_fields else 0

    def save(self, *args, **kwargs):
        super(UserScore, self).save(*args, **kwargs)
        self.nabra_user.calculate_average_score()
    
    class Meta:
        unique_together = (("surah_num", "aya_num", "nabra_user"),)
        db_table = "user_score"
        
def generate_unique_filename(instance, filename):
    ext = filename.split('.')[-1]
    random_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    user_id = NabraUser.objects.get(email__iexact=instance.email)
    new_filename = f"{instance.surah_num}_{instance.ayah_num}_{user_id}_{random_id}.{ext}"
    return os.path.join('', new_filename)

class AudioFile(models.Model):
    SURAH_CHOICES = (
        (1, "Al-Fatiha"),
        (87,"Al-A'la"),
        (88, "Al-Ghashiyah"),
        (89, "Al-Fajr"),
        (90, "Al-Balad"),
        (91, "Ash-Shams"),
        (92, "Al-Lail"),
        (93, "Ad-Duha"),
        (94, "Ash-Sharh"),
        (95, "At-Tin"),
        (96, "Al-Alaq"),
        (97, "Al-Qadr"),
        (98, "Al-Bayyinah"),
        (99, "Az-Zalzalah"),
        (100, "Al-Adiyat"),
        (101, "Al-Qari'ah"),
        (102, "At-Takathur"),
        (103, "Al-Asr"),
        (104, "Al-Humazah"),
        (105, "Al-Fil"),
        (106, "Quraish"),
        (107, "Al-Ma'un"),
        (108, "Al-Kawthar"),
        (109, "Al-Kafirun"),
        (110, "An-Nasr"),
        (111, "Al-Masad"),
        (112, "Al-Ikhlas"),
        (113, "Al-Falaq"),
        (114, "An-Nas"), )

    audio_file = models.FileField(upload_to=generate_unique_filename)
    surah_num = models.IntegerField(choices=SURAH_CHOICES)
    ayah_num = models.IntegerField()
    email = models.EmailField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Surah {self.surah_num}, Ayah {self.ayah_num} - {self.email}"
