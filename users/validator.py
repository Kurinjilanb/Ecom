# -*- coding: utf-8 -*-
import re

from django.core.exceptions import ValidationError





def phone_number_validator(value):
    """
    Allows only digits, '+', '-', and space.
    """
    pattern = r'^[0-9+\- ]*$'

    if not re.match(pattern, value):
        raise ValidationError("Only digits, '+' and '-' are allowed.")

