from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

Usuario = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Buscamos si lo que ingresó coincide con el username O con el email
            user = Usuario.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except Usuario.DoesNotExist:
            return None

        # Si el usuario existe, verificamos su contraseña
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None