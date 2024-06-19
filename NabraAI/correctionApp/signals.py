from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UserScore

@receiver(post_save, sender=UserScore)
@receiver(post_delete, sender=UserScore)
def update_user_score(sender, instance, **kwargs):
    instance.nabra_user.calculate_average_score()