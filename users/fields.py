from django.db.models import EmailField



class CustomEmailField(EmailField):
    """
    Custom email field for disallowing blacklisted email domains.
    """
    description = ("Email address")

