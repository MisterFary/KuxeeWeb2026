def oficios_globales(request):
    """
    Hace disponible la lista de oficios en TODOS los templates del proyecto,
    sin necesidad de pasarla manualmente en cada vista.
    """
    from .forms import LISTA_OFICIOS
    return {
        'oficios_global': LISTA_OFICIOS[1:] 
    }


def notificaciones_globales(request):
    if request.user.is_authenticated:
        from .models import Notificacion
        
        # 1. Primero contamos TODAS las no leídas directamente a la base de datos
        no_leidas = Notificacion.objects.filter(usuario=request.user, leida=False).count()
        
        # 2. Luego traemos solo las últimas 10 para mostrarlas en el menú
        notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha_creacion')[:10]
        
        return {
            'mis_notificaciones': notificaciones,
            'notificaciones_no_leidas': no_leidas
        }
    return {}