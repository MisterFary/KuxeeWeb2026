import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, get_user_model
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.cache import cache         
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDay, TruncMonth
from datetime import timedelta
from .models import Trato
from .models import SolicitudCliente
from django.db.models import Avg
from .models import Resena
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Trato


from .models import (
    PerfilCliente, 
    PerfilMaestro, 
    Servicio, 
    Comentario, 
    Notificacion, 
    MensajeDirecto, 
    Trato,
    ContadorVisitas,
    SolicitudCliente,  
    ArchivoSolicitud,
    BannerDestacado
)
from .forms import RegistroKuxeeForm, LISTA_OFICIOS, REGIONES_Y_COMUNAS

Usuario = get_user_model()


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def es_admin(user):
    return user.is_superuser


# ==========================================
# VISTAS PRINCIPALES
# ==========================================
def inicio(request):
    # Sumar una visita al contador global
    contador, created = ContadorVisitas.objects.get_or_create(id=1)
    contador.visitas += 1
    contador.save()

    now = timezone.now()
    
    # Obtener únicamente los banners activos cuya fecha de expiración sea mayor a la actual
    banners_activos = BannerDestacado.objects.filter(
        estado='activo', 
        fecha_expiracion__gt=now
    ).order_by('posicion')
    
    # --- NUEVA LÓGICA DE DISPONIBILIDAD DE BANNERS ---
    precios_banner = {1: 8990, 2: 7990, 3: 6990, 4: 5990, 5: 4990, 6: 3990, 7: 2990}
    emojis_banner = {1: '🥇', 2: '🥈', 3: '🥉', 4: '📍', 5: '📍', 6: '📍', 7: '📍'}
    ocupados = {b.posicion: b for b in banners_activos}
    
    disponibilidad_banners = []
    for i in range(1, 8):
        if i in ocupados:
            banner = ocupados[i]
            diferencia = banner.fecha_expiracion - now
            dias = diferencia.days
            horas = diferencia.seconds // 3600
            mensaje = f"Disponible en {dias} días y {horas} hrs" if dias > 0 else f"Disponible en {horas} hrs"
            disponibilidad = False
        else:
            mensaje = "Disponible ahora - Publicación rápida"
            disponibilidad = True
            
        disponibilidad_banners.append({
            'posicion': i,
            'precio': precios_banner[i],
            'emoji': emojis_banner[i],
            'disponible': disponibilidad,
            'mensaje': mensaje
        })
    # -------------------------------------------------

    maestros = PerfilMaestro.objects.select_related('usuario').order_by('-id')[:6]
    servicios = Servicio.objects.select_related('maestro__usuario').order_by('-fecha_publicacion')[:6]
    
    return render(request, 'usuarios/index.html', {
        'maestros': maestros, 
        'servicios': servicios,
        'banners': banners_activos,
        'disponibilidad_banners': disponibilidad_banners
    })


def lista_maestros(request):
    maestros = PerfilMaestro.objects.select_related('usuario').all().order_by('-id')
    oficio = request.GET.get('oficio')
    comuna = request.GET.get('comuna')

    if oficio:
        maestros = maestros.filter(oficio_principal__icontains=oficio)
    if comuna:
        maestros = maestros.filter(comuna__icontains=comuna)

    return render(request, 'usuarios/maestros.html', {
        'maestros': maestros,
        'oficios': LISTA_OFICIOS[1:],
        'regiones': REGIONES_Y_COMUNAS[1:],
        'oficio_seleccionado': oficio or '',
        'comuna_seleccionada': comuna or '',
    })


def lista_servicios(request):
    servicios = Servicio.objects.select_related('maestro__usuario').order_by('-fecha_publicacion')
    
    oficios_seleccionados = request.GET.getlist('oficio')
    comunas_seleccionadas = request.GET.getlist('comuna')

    if oficios_seleccionados:
        query_oficios = Q()
        for o in oficios_seleccionados:
            query_oficios |= Q(oficio__icontains=o)
        servicios = servicios.filter(query_oficios)
        
    if comunas_seleccionadas:
        query_comunas = Q()
        for c in comunas_seleccionadas:
            query_comunas |= Q(maestro__comuna__icontains=c)
        servicios = servicios.filter(query_comunas)

    return render(request, 'usuarios/servicios.html', {
        'servicios': servicios.distinct(),
        'oficios': LISTA_OFICIOS[1:],
        'regiones': REGIONES_Y_COMUNAS[1:],
        'oficios_seleccionados': oficios_seleccionados,
        'comunas_seleccionadas': comunas_seleccionadas,
    })


def lista_solicitudes(request):
    solicitudes = SolicitudCliente.objects.filter(activa=True).order_by('-fecha_creacion')
    
    busqueda = request.GET.get('q')
    oficio = request.GET.get('oficio')
    comuna = request.GET.get('comuna')
    
    if busqueda:
        solicitudes = solicitudes.filter(titulo__icontains=busqueda)
    if oficio and oficio != 'Todos los oficios':
        solicitudes = solicitudes.filter(oficio_requerido__icontains=oficio)
    if comuna and comuna != 'Todas las comunas':
        solicitudes = solicitudes.filter(cliente__comuna__icontains=comuna)

    return render(request, 'usuarios/solicitudes.html', {
        'solicitudes': solicitudes,
        'oficios': LISTA_OFICIOS[1:],
        'regiones': REGIONES_Y_COMUNAS[1:]
    })

@login_required
def publicar_solicitud(request):
    if not hasattr(request.user, 'perfil_cliente'):
        messages.error(request, 'Solo los clientes pueden publicar solicitudes.')
        return redirect('inicio')
        
    perfil = request.user.perfil_cliente
    if perfil.plan_actual != 'premium':
        messages.error(request, 'Debes ser Cliente Premium para publicar solicitudes.')
        return redirect('planes')

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        oficio = request.POST.get('oficio')
        archivos = request.FILES.getlist('archivos')

        if len(archivos) > 10:
            messages.error(request, 'Puedes subir un máximo de 10 archivos.')
            return redirect('publicar_solicitud')

        solicitud = SolicitudCliente.objects.create(
            cliente=perfil,
            titulo=titulo,
            descripcion=descripcion,
            oficio_requerido=oficio
        )

        for archivo in archivos:
            ArchivoSolicitud.objects.create(solicitud=solicitud, archivo=archivo)

        messages.success(request, '¡Tu solicitud fue publicada exitosamente!')
        return redirect('solicitudes')

    return render(request, 'usuarios/publicar_solicitud.html', {'oficios': LISTA_OFICIOS[1:]})


def planes(request):
    return render(request, 'usuarios/planes.html')


def registrar_usuario(request):
    if request.method == 'POST':
        form = RegistroKuxeeForm(request.POST)
        if form.is_valid():
            rol = request.POST.get('rol', 'cliente')
            comunas_lista = request.POST.getlist('comunas')
            comunas_str = ", ".join(comunas_lista)
            oficios_lista = request.POST.getlist('oficios')
            oficios_str = ", ".join(oficios_lista)
            
            try:
                with transaction.atomic():
                    usuario = Usuario.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['contrasena'],
                        first_name=form.cleaned_data['first_name'],
                        es_cliente=(rol == 'cliente'),
                        es_maestro=(rol == 'maestro'),
                    )

                    if rol == 'maestro':
                        PerfilMaestro.objects.create(
                            usuario=usuario,
                            telefono=form.cleaned_data['telefono'],
                            comuna=comunas_str,
                            oficio_principal=oficios_str
                        )
                    else:
                        PerfilCliente.objects.create(
                            usuario=usuario,
                            telefono=form.cleaned_data['telefono'],
                            comuna=comunas_str
                        )

                login(request, usuario, backend='usuarios.backends.EmailOrUsernameModelBackend')
                messages.success(request, f'¡Bienvenido a Kuxee, {usuario.first_name}!')
                return redirect('inicio')
            except Exception as e:
                messages.error(request, f'Hubo un error: {str(e)}')
        else:
            for campo, errores in form.errors.items():
                for error in errores:
                    messages.error(request, error)
    else:
        form = RegistroKuxeeForm()
        
    return render(request, 'usuarios/registro.html', {'form': form})


@login_required
def publicar_servicio(request):
    if request.method == 'POST':
        if not hasattr(request.user, 'perfil_maestro'):
            messages.error(request, 'Debes estar registrado como maestro.')
            return redirect('inicio')

        perfil = request.user.perfil_maestro
        es_plus = perfil.plan_actual == 'plus'
        
        limite_servicios = 6 if es_plus else 3
        limite_oficios = 6 if es_plus else 3
        limite_imagenes = 14 if es_plus else 7
        
        if Servicio.objects.filter(maestro=perfil).count() >= limite_servicios:
            messages.error(request, f'Llegaste al límite de {limite_servicios} servicios para tu plan. ¡Suscríbete a Plus para publicar más!')
            return redirect('planes')

        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        oficios = request.POST.getlist('oficios') or request.POST.get('oficio')
        
        if isinstance(oficios, list) and len(oficios) > limite_oficios:
            messages.error(request, f'Solo puedes seleccionar hasta {limite_oficios} oficios con tu plan actual.')
            return redirect('publicar_servicio')
            
        oficio_final = ", ".join(oficios) if isinstance(oficios, list) else oficios
        precio = request.POST.get('precio') or None
        imagenes = request.FILES.getlist('imagenes')
        
        if len(imagenes) > limite_imagenes:
            messages.error(request, f'Solo puedes subir hasta {limite_imagenes} imágenes por servicio con tu plan actual.')
            return redirect('publicar_servicio')
            
        imagen_principal = imagenes[0] if imagenes else None

        Servicio.objects.create(
            maestro=perfil,
            titulo=titulo,
            oficio=oficio_final,
            descripcion=descripcion,
            precio_base=precio,
            imagen_portada=imagen_principal
        )
        messages.success(request, '¡Tu servicio se publicó correctamente!')
        return redirect('inicio')
    return render(request, 'usuarios/publicar_servicio.html', {'oficios': LISTA_OFICIOS[1:]})


@login_required
def mi_perfil(request):
    perfil_maestro = getattr(request.user, 'perfil_maestro', None)
    
    # Servicio.maestro requiere PerfilMaestro (perfil_maestro)
    servicios = Servicio.objects.filter(maestro=perfil_maestro) if (request.user.es_maestro and perfil_maestro) else []
    
    solicitudes = []
    if request.user.es_cliente and hasattr(request.user, 'perfil_cliente'):
        solicitudes = SolicitudCliente.objects.filter(cliente=request.user.perfil_cliente)
        
    # Trato.maestro requiere Usuario (request.user)
    tratos_realizados = Trato.objects.filter(maestro=request.user, estado='finalizado').count() if request.user.es_maestro else 0
    
    # Resena.maestro requiere Usuario (request.user)
    promedio = Resena.objects.filter(maestro=request.user).aggregate(Avg('calificacion'))['calificacion__avg']
    promedio_calificacion = round(promedio, 1) if promedio else 0

    contexto = {
        'user': request.user,
        'servicios': servicios,
        'solicitudes': solicitudes,
        'tratos_realizados': tratos_realizados,
        'promedio_calificacion': promedio_calificacion,
    }
    return render(request, 'usuarios/mi_perfil.html', contexto)


@login_required
def actualizar_avatar(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        request.user.foto_perfil = request.FILES['avatar']
        request.user.save()
        messages.success(request, '¡Foto de perfil actualizada exitosamente!')
    return redirect('mi_perfil')


@login_required
def eliminar_servicio(request, servicio_id):
    if request.method == 'POST':
        servicio = get_object_or_404(Servicio, id=servicio_id, maestro__usuario=request.user)
        servicio.delete()
        messages.success(request, 'Servicio eliminado.')
    return redirect('mi_perfil')


@login_required
def editar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, maestro__usuario=request.user)
    if request.method == 'POST':
        servicio.titulo = request.POST.get('titulo')
        servicio.descripcion = request.POST.get('descripcion')
        oficios = request.POST.getlist('oficios') or request.POST.get('oficio')
        if oficios:
            servicio.oficio = ", ".join(oficios) if isinstance(oficios, list) else oficios
        
        precio = request.POST.get('precio')
        servicio.precio_base = precio if precio else None
        imagenes = request.FILES.getlist('imagenes')
        if imagenes:
            servicio.imagen_portada = imagenes[0]

        servicio.save()
        messages.success(request, '¡Servicio actualizado!')
        return redirect('mi_perfil')
    return render(request, 'usuarios/editar_servicio.html', {'servicio': servicio, 'oficios': LISTA_OFICIOS[1:]})


@login_required
def editar_perfil(request):
    usuario = request.user
    if request.method == 'POST':
        usuario.first_name = request.POST.get('first_name', '')
        usuario.last_name = request.POST.get('last_name', '')
        usuario.save()

        if hasattr(usuario, 'perfil_maestro'):
            perfil = usuario.perfil_maestro
            perfil.telefono = request.POST.get('telefono', '')
            perfil.comuna = request.POST.get('comuna', '')
            perfil.descripcion = request.POST.get('descripcion', '')
            perfil.save()
        elif hasattr(usuario, 'perfil_cliente'):
            perfil = usuario.perfil_cliente
            perfil.telefono = request.POST.get('telefono', '')
            perfil.comuna = request.POST.get('comuna', '')
            perfil.save()
            
        messages.success(request, '¡Tu perfil ha sido actualizado exitosamente!')
        return redirect('mi_perfil')
    return render(request, 'usuarios/editar_perfil.html', {'regiones': REGIONES_Y_COMUNAS[1:]})


def perfil_publico(request, username):
    maestro_user = get_object_or_404(Usuario, username=username, es_maestro=True)
    perfil = get_object_or_404(PerfilMaestro, usuario=maestro_user)
    
    # Servicio.maestro requiere PerfilMaestro (perfil)
    servicios = Servicio.objects.filter(maestro=perfil)
    
    # Trato.maestro requiere Usuario (maestro_user)
    tratos_realizados = Trato.objects.filter(maestro=maestro_user, estado='finalizado').count()
    
    # Resena.maestro requiere Usuario (maestro_user)
    promedio = Resena.objects.filter(maestro=maestro_user).aggregate(Avg('calificacion'))['calificacion__avg']
    promedio_calificacion = round(promedio, 1) if promedio else 0

    contexto = {
        'maestro_user': maestro_user,
        'perfil': perfil,
        'servicios': servicios,
        'tratos_realizados': tratos_realizados,
        'promedio_calificacion': promedio_calificacion,
    }
    return render(request, 'usuarios/perfil_publico.html', contexto)


def detalle_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio.objects.select_related('maestro__usuario'), id=servicio_id)
    otros_servicios = Servicio.objects.filter(maestro=servicio.maestro).exclude(id=servicio.id).order_by('-fecha_publicacion')[:4]
    comentarios = servicio.comentarios.filter(parent__isnull=True).select_related('autor').order_by('-fecha_creacion')
    return render(request, 'usuarios/detalle_servicio.html', {
        'servicio': servicio,
        'otros_servicios': otros_servicios,
        'comentarios': comentarios
    })


@login_required
def agregar_comentario(request, servicio_id):
    if request.method == 'POST':
        servicio = get_object_or_404(Servicio, id=servicio_id)
        texto = request.POST.get('texto', '').strip()
        parent_id = request.POST.get('parent_id')
        
        if texto:
            parent_obj = get_object_or_404(Comentario, id=parent_id) if parent_id else None
            nuevo_comentario = Comentario.objects.create(
                servicio=servicio,
                autor=request.user,
                texto=texto,
                parent=parent_obj
            )
            
            enlace_servicio = f"/servicio/{servicio.id}/"
            if parent_obj:
                if parent_obj.autor != request.user:
                    Notificacion.objects.create(
                        usuario=parent_obj.autor,
                        comentario=nuevo_comentario,
                        mensaje=f"{request.user.first_name or request.user.username} ha respondido a tu comentario en '{servicio.titulo}'.",
                        enlace=enlace_servicio
                    )
                messages.success(request, 'Respuesta publicada correctamente.')
            else:
                if servicio.maestro.usuario != request.user:
                    Notificacion.objects.create(
                        usuario=servicio.maestro.usuario,
                        comentario=nuevo_comentario,
                        mensaje=f"{request.user.first_name or request.user.username} ha preguntado en tu servicio '{servicio.titulo}'.",
                        enlace=enlace_servicio
                    )
                messages.success(request, 'Comentario publicado correctamente.')
        else:
            messages.error(request, 'El texto no puede estar vacío.')
    return redirect('detalle_servicio', servicio_id=servicio_id)


@login_required
def leer_notificacion(request, notificacion_id):
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
    notificacion.leida = True
    notificacion.save()
    if notificacion.enlace:
        return redirect(notificacion.enlace)
    return redirect('inicio')


@login_required
def en_construccion(request):
    messages.info(request, 'Esta sección estará disponible muy pronto. ¡Estamos trabajando en ella!')
    return redirect('mi_perfil')


@login_required
def marcar_notificacion_leida(request, notificacion_id):
    if request.method == 'POST':
        notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
        notificacion.leida = True
        notificacion.save()
    return redirect(request.META.get('HTTP_REFERER', 'inicio'))


@login_required
def eliminar_notificacion(request, notificacion_id):
    if request.method == 'POST':
        notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
        notificacion.delete()
    return redirect(request.META.get('HTTP_REFERER', 'inicio'))


@login_required
def mis_trabajos(request):
    estado_actual = request.GET.get('estado', 'todos')
    
    if request.method == 'POST':
        trato_id = request.POST.get('trato_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        
        trato = Trato.objects.filter(id=trato_id, cliente=request.user).first()
        
        if trato and nuevo_estado in ['en_proceso', 'finalizado', 'cancelado', 'pospuesto']:
            trato.estado = nuevo_estado
            trato.save()
            messages.success(request, f'¡El estado del trabajo se actualizó exitosamente!')
            
        return redirect(f"{reverse('mis_trabajos')}?estado={estado_actual}")

    tratos = Trato.objects.filter(Q(cliente=request.user) | Q(maestro=request.user)).order_by('-fecha_creacion')

    if estado_actual == 'proceso':
        tratos = tratos.filter(estado__in=['pagado', 'en_proceso'])
    elif estado_actual == 'finalizado':
        tratos = tratos.filter(estado='finalizado')
    elif estado_actual == 'cancelado':
        tratos = tratos.filter(estado__in=['pendiente', 'en_espera', 'cancelado', 'pospuesto'])

    return render(request, 'usuarios/mis_trabajos.html', {
        'estado_actual': estado_actual,
        'tratos': tratos
    })


@login_required
def mis_mensajes(request):
    contacto_username = request.GET.get('contacto')
    servicio_id = request.GET.get('servicio')
    
    contacto_activo = None
    if contacto_username:
        contacto_activo = Usuario.objects.filter(username=contacto_username).first()
        
    servicio_activo = None
    if servicio_id:
        servicio_activo = Servicio.objects.filter(id=servicio_id).first()
        
    mensajes = []
    conversaciones = []
    otro_escribiendo = False
    
    trato_pendiente = None
    trato_pagado = None
    if servicio_activo and contacto_activo:
        trato_pendiente = Trato.objects.filter(
            servicio=servicio_activo,
            estado__in=['pendiente', 'en_espera']
        ).filter(
            Q(cliente=request.user, maestro=contacto_activo) | 
            Q(cliente=contacto_activo, maestro=request.user)
        ).first()

        trato_pagado = Trato.objects.filter(
            servicio=servicio_activo,
            estado='pagado'
        ).filter(
            Q(cliente=request.user, maestro=contacto_activo) | 
            Q(cliente=contacto_activo, maestro=request.user)
        ).first()

    if request.method == 'POST' and request.POST.get('accion') == 'escribiendo' and contacto_activo:
        clave_cache = f"typing_{request.user.username}_{contacto_activo.username}"
        cache.set(clave_cache, True, timeout=5)
        return JsonResponse({'status': 'ok'})

    if request.method == 'POST' and contacto_activo and not request.POST.get('accion'):
        contenido = request.POST.get('contenido', '').strip()
        
        if contenido:
            if not trato_pagado:
                texto_lower = contenido.lower()
                
                patron_correo = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                patron_telefono = r'(?<!\$)\b(\+?56\s?)?(9\s?)?[2-9]\d{7,8}\b(?!\s*(mil|pesos|clp))'
                patron_direccion = r'\b(direccion|dirección|ubicacion|ubicación|calle|avenida|av|pasaje|psje|departamento|depto|piso|n°|nro|block|blq|casa|cs|villa|poblacion|población|sector|num|número|lote|sitio|condominio)\b\s*([a-záéíóúñ]+\s*){0,6}#?\s*\d{1,5}\b'
                
                es_correo = re.search(patron_correo, texto_lower)
                es_telefono = re.search(patron_telefono, texto_lower)
                es_direccion = re.search(patron_direccion, texto_lower)

                if es_correo or es_telefono or es_direccion:
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({
                            'status': 'error', 
                            'msg': 'Por seguridad, no puedes compartir teléfonos, correos o direcciones antes de pagar la comisión.'
                        })
                    else:
                        messages.error(request, 'Por seguridad, no puedes compartir teléfonos, correos o direcciones antes de pagar la comisión.')
                        return redirect(f"{request.path}?contacto={contacto_username}&servicio={servicio_id or ''}")

            MensajeDirecto.objects.create(
                remitente=request.user,
                destinatario=contacto_activo,
                servicio=servicio_activo,
                contenido=contenido
            )
            
            enlace_chat = f"{reverse('mensajes')}?contacto={request.user.username}"
            if servicio_activo:
                enlace_chat += f"&servicio={servicio_activo.id}"
                
            Notificacion.objects.filter(
                usuario=contacto_activo,
                enlace__startswith=f"{reverse('mensajes')}?contacto={request.user.username}",
                leida=False
            ).delete()
            
            Notificacion.objects.create(
                usuario=contacto_activo,
                mensaje=f"Tienes un nuevo mensaje de {request.user.first_name or request.user.username}.",
                enlace=enlace_chat
            )
            
            cache.delete(f"typing_{request.user.username}_{contacto_activo.username}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'mensaje_guardado'})
            return redirect(f"{request.path}?contacto={contacto_username}&servicio={servicio_id or ''}")

    if contacto_activo:
        mensajes = MensajeDirecto.objects.filter(
            Q(remitente=request.user, destinatario=contacto_activo) |
            Q(remitente=contacto_activo, destinatario=request.user)
        ).order_by('fecha_envio')
        otro_escribiendo = cache.get(f"typing_{contacto_activo.username}_{request.user.username}", False)
        
    mensajes_historial = MensajeDirecto.objects.filter(Q(remitente=request.user) | Q(destinatario=request.user))
    contactos_unicos = set()
    for msg in mensajes_historial:
        if msg.remitente == request.user:
            contactos_unicos.add(msg.destinatario)
        else:
            contactos_unicos.add(msg.remitente)
            
    for contacto in contactos_unicos:
        ultimo_msg = MensajeDirecto.objects.filter(
            Q(remitente=request.user, destinatario=contacto) | Q(remitente=contacto, destinatario=request.user)
        ).order_by('-fecha_envio').first()
        conversaciones.append({'contacto': contacto, 'ultimo_mensaje': ultimo_msg})
        
    conversaciones.sort(key=lambda x: x['ultimo_mensaje'].fecha_envio, reverse=True)
    
    context = {
        'contacto_activo': contacto_activo,
        'servicio_activo': servicio_activo,
        'mensajes': mensajes,
        'conversaciones': conversaciones,
        'otro_escribiendo': otro_escribiendo,
        'trato_pendiente': trato_pendiente,
        'trato_pagado': trato_pagado,
    }
    return render(request, 'usuarios/mensajes.html', context)


def acceso_denegado(request):
    return render(request, 'usuarios/acceso_denegado.html')


# ==========================================
# RUTAS PARA EL SISTEMA DE TRATOS Y PAGOS
# ==========================================

@login_required
def guardar_rut(request):
    if request.method == 'POST':
        rut = request.POST.get('rut')
        if rut:
            request.user.rut = rut
            request.user.save()
            return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def gestionar_trato(request):
    if request.method == 'POST':
        contacto_username = request.POST.get('contacto')
        servicio_id = request.POST.get('servicio_id')
        accion = request.POST.get('accion') 
        
        contacto = get_object_or_404(Usuario, username=contacto_username)
        servicio = get_object_or_404(Servicio, id=servicio_id)
        
        es_el_maestro = (request.user == servicio.maestro.usuario)
        
        if accion == 'iniciar_y_pagar':
            if es_el_maestro:
                return JsonResponse({'status': 'error', 'msg': 'Acceso denegado.'}, status=403)
            
            trato = Trato.objects.filter(servicio=servicio, cliente=request.user, estado__in=['pendiente', 'en_espera']).first()
            
            es_premium = False
            if hasattr(request.user, 'perfil_cliente'):
                es_premium = request.user.perfil_cliente.plan_actual == 'premium'
            
            comision_texto = "$5.990" if es_premium else "$9.990"
            
            if not trato:
                trato = Trato.objects.create(servicio=servicio, cliente=request.user, maestro=contacto, estado='en_espera')
                MensajeDirecto.objects.create(
                    remitente=request.user,
                    destinatario=contacto,
                    servicio=servicio,
                    contenido=f"El cliente inició un trato. Está pagando la comisión a Kuxee ({comision_texto} CLP).",
                    es_sistema=True,
                    tipo_sistema='warning'
                )
            else:
                trato.estado = 'en_espera'
                trato.save()
                
            return JsonResponse({'status': 'redirect', 'url': reverse('pasarela_pago', args=[trato.id])})

        elif accion == 'ir_a_pagar':
            if es_el_maestro:
                return JsonResponse({'status': 'error', 'msg': 'Acceso denegado.'}, status=403)
            
            trato = Trato.objects.filter(servicio=servicio, cliente=request.user, estado__in=['pendiente', 'en_espera']).first()
            if trato:
                trato.estado = 'en_espera'
                trato.save()
            return JsonResponse({'status': 'redirect', 'url': reverse('pasarela_pago', args=[trato.id])})

        elif accion == 'volver_pasarela':
            if es_el_maestro:
                return JsonResponse({'status': 'error', 'msg': 'Acceso denegado.'}, status=403)
            
            trato = Trato.objects.filter(servicio=servicio, cliente=request.user, estado='en_espera').first()
            if trato:
                trato.estado = 'pendiente'
                trato.save()
            return JsonResponse({'status': 'ok'})

        elif accion == 'cancelar':
            trato = Trato.objects.filter(
                servicio=servicio,
                estado__in=['pendiente', 'en_espera']
            ).filter(
                Q(cliente=request.user, maestro=contacto) | Q(cliente=contacto, maestro=request.user)
            ).first()
            
            if trato:
                trato.estado = 'cancelado'
                trato.save()
                MensajeDirecto.objects.create(
                    remitente=request.user,
                    destinatario=contacto,
                    servicio=servicio,
                    contenido="❌ Se canceló el trato propuesto.",
                    es_sistema=True,
                    tipo_sistema='danger'
                )

        elif accion == 'pagar':
            if es_el_maestro:
                return JsonResponse({'status': 'error', 'msg': 'Acceso denegado.'}, status=403)
            
            trato = Trato.objects.filter(servicio=servicio, cliente=request.user, estado='en_espera').first()
            if trato:
                trato.estado = 'pagado'
                trato.save()
                MensajeDirecto.objects.create(
                    remitente=request.user,
                    destinatario=contacto,
                    servicio=servicio,
                    contenido="✅ Trato realizado.",
                    es_sistema=True,
                    tipo_sistema='success'
                )

        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def pasarela_pago(request, trato_id):
    trato = get_object_or_404(Trato, id=trato_id, cliente=request.user)
    if trato.estado == 'pagado':
        return redirect(f"{reverse('mensajes')}?contacto={trato.maestro.username}&servicio={trato.servicio.id}")
    return render(request, 'usuarios/pasarela_pago.html', {'trato': trato})

# ==========================================
# RUTAS PARA LA SUSCRIPCIÓN PLUS / PREMIUM
# ==========================================

@login_required
def pasarela_suscripcion(request):
    if not hasattr(request.user, 'perfil_maestro') and not hasattr(request.user, 'perfil_cliente'):
        return redirect('inicio')
    return render(request, 'usuarios/pasarela_suscripcion.html')

@login_required
def procesar_pago_suscripcion(request):
    if request.method == 'POST':
        if hasattr(request.user, 'perfil_maestro'):
            perfil = request.user.perfil_maestro
            perfil.plan_actual = 'plus'
            perfil.save()
            messages.success(request, '¡Felicidades! Ahora eres Maestro Plus.')
            return JsonResponse({'status': 'ok'})
            
        elif hasattr(request.user, 'perfil_cliente'):
            perfil = request.user.perfil_cliente
            perfil.plan_actual = 'premium'
            perfil.save()
            messages.success(request, '¡Felicidades! Ahora eres Cliente Premium.')
            return JsonResponse({'status': 'ok'})
            
    return JsonResponse({'status': 'error'}, status=400)


# ==========================================
# RUTAS PARA LA COMPRA DE BANNERS (MAESTROS)
# ==========================================

@login_required
def procesar_pago_banner(request):
    if request.method == 'POST':
        
        # --- PASO 2: EL CLIENTE CONFIRMÓ EL PAGO EN LA PASARELA ---
        if 'pagar_banner_id' in request.POST:
            banner_id = request.POST.get('pagar_banner_id')
            banner = get_object_or_404(BannerDestacado, id=banner_id, usuario=request.user)
            
            # Cambiamos el estado para que te aparezca en el Panel Admin
            banner.estado = 'en_diseno' 
            banner.save()
            
            messages.success(request, f'¡Pago exitoso de ${banner.monto_pagado}! Tu banner está en proceso.')
            return redirect('inicio')

        # --- PASO 1: EL CLIENTE VIENE DEL MODAL Y VA A LA PASARELA ---
        else:
            dias = int(request.POST.get('dias', 0))
            posicion = int(request.POST.get('posicion', 0))
            total_a_pagar = int(request.POST.get('total_a_pagar', 0))
            tipo_foto = request.POST.get('tipo_foto')
            detalles = request.POST.get('detalles', '')
            now = timezone.now()

            # --- NUEVA VALIDACIÓN: BLOQUEAR COMPRA SI ESTÁ OCUPADO ---
            banner_ocupado = BannerDestacado.objects.filter(
                estado='activo',
                posicion=posicion,
                fecha_expiracion__gt=now
            ).order_by('-fecha_expiracion').first()
            
            if banner_ocupado:
                diferencia = banner_ocupado.fecha_expiracion - now
                dias_restantes = diferencia.days
                horas_restantes = diferencia.seconds // 3600
                tiempo_msg = f"{dias_restantes} días y {horas_restantes} horas" if dias_restantes > 0 else f"{horas_restantes} horas"
                
                messages.error(request, f'❌ El {posicion}º Lugar del carrusel está ocupado actualmente. Estará disponible en {tiempo_msg}. Por favor, elige otro lugar.')
                return redirect('inicio')

            # Se crea el banner pero aún NO está pagado
            banner = BannerDestacado(
                usuario=request.user,
                dias_contratados=dias,
                posicion=posicion,
                detalles_diseno=detalles,
                monto_pagado=total_a_pagar,
                estado='pendiente_pago' 
            )

            if tipo_foto == 'perfil':
                banner.usar_foto_perfil = True
            else:
                foto_nueva = request.FILES.get('foto_nueva')
                if foto_nueva:
                    banner.foto_referencia = foto_nueva

            banner.save()

            return render(request, 'usuarios/pago_banner.html', {'banner': banner})


@login_required
def pasarela_pago_banner(request, banner_id):
    banner = get_object_or_404(BannerDestacado, id=banner_id, usuario=request.user)
    
    if request.method == 'POST':
        # Simulación: El pago fue exitoso
        banner.estado = 'en_diseno'  # Pasa al panel del admin para que suba la foto oficial
        banner.save()
        messages.success(request, '¡Pago realizado con éxito! Nos pondremos en marcha con tu diseño del banner.')
        return redirect('inicio')
        
    total = request.session.get('banner_pago_total', 0)
    return render(request, 'usuarios/pasarela_pago_banner.html', {'banner': banner, 'total': total})


# ==========================================
# PANEL DE ADMINISTRACIÓN
# ==========================================

@user_passes_test(es_admin)
def panel_admin(request):
    now = timezone.now()
    
    if request.method == 'POST':
        # --- Cambiar plan de maestro ---
        if 'cambiar_plan_maestro' in request.POST:
            maestro_id = request.POST.get('maestro_id')
            nuevo_plan = request.POST.get('nuevo_plan')
            maestro = get_object_or_404(PerfilMaestro, id=maestro_id)
            maestro.plan_actual = nuevo_plan
            maestro.save()
            messages.success(request, f'¡Plan actualizado a {nuevo_plan.upper()} para el maestro {maestro.usuario.username}!')
            return redirect('panel_admin')
            
        # --- Cambiar plan de cliente ---
        elif 'cambiar_plan_cliente' in request.POST:
            cliente_id = request.POST.get('cliente_id')
            nuevo_plan = request.POST.get('nuevo_plan')
            cliente = get_object_or_404(PerfilCliente, id=cliente_id)
            cliente.plan_actual = nuevo_plan
            cliente.save()
            messages.success(request, f'¡Plan actualizado a {nuevo_plan.upper()} para el cliente {cliente.usuario.username}!')
            return redirect('panel_admin')

        # --- GUARDAR BANNER ---
        elif 'guardar_banner' in request.POST:
            banner_id = request.POST.get('banner_id')
            banner = get_object_or_404(BannerDestacado, id=banner_id)
            
            banner_ocupante = BannerDestacado.objects.filter(
                estado='activo',
                posicion=banner.posicion,
                fecha_expiracion__gt=now
            ).order_by('-fecha_expiracion').first()
            
            if banner_ocupante:
                diferencia = banner_ocupante.fecha_expiracion - now
                dias = diferencia.days
                horas = diferencia.seconds // 3600
                tiempo_msg = f"{dias} días y {horas} horas" if dias > 0 else f"{horas} horas"
                messages.error(request, f'❌ No se puede publicar: El {banner.posicion}º Lugar está ocupado actualmente. Estará disponible en {tiempo_msg}.')
                return redirect('panel_admin')
            
            imagen = request.FILES.get('imagen_final')
            if imagen:
                banner.imagen_final_banner = imagen
            
            banner.titulo_banner = request.POST.get('titulo_banner', '').strip()
            banner.texto_banner = request.POST.get('texto_banner', '').strip()
            
            banner.estado = 'activo'
            banner.save()
            messages.success(request, f'¡Banner activado y publicado para {banner.usuario.username}!')
            return redirect('panel_admin')

    # =========================================================
    # 1. ESTADÍSTICAS GENERALES Y CÁLCULO DINÁMICO DE TRATOS
    # =========================================================
    tratos_exitosos = Trato.objects.filter(estado__in=['pagado', 'en_proceso', 'finalizado'])
    
    ingresos_tratos = 0
    ingresos_tratos_mes = 0
    ingresos_tratos_hoy = 0 
    tratos_mes = 0
    tratos_hoy_count = 0   
    ganancias_tratos_dict = {}

    for trato in tratos_exitosos:
        precio = 9990 
        if hasattr(trato.cliente, 'perfil_cliente'):
            if trato.cliente.perfil_cliente.plan_actual == 'premium':
                precio = 5990 
        
        ingresos_tratos += precio
        
        # Verificar si es trato de este mes
        if trato.fecha_creacion.year == now.year and trato.fecha_creacion.month == now.month:
            ingresos_tratos_mes += precio
            tratos_mes += 1
            
        # Verificar si es trato de HOY (Día actual)
        if trato.fecha_creacion.date() == now.date():
            ingresos_tratos_hoy += precio
            tratos_hoy_count += 1
            
        # Agrupar para el gráfico de 6 meses
        mes_key = (trato.fecha_creacion.year, trato.fecha_creacion.month)
        ganancias_tratos_dict[mes_key] = ganancias_tratos_dict.get(mes_key, 0) + precio

    # Totales históricos de planes
    maestros_plus = PerfilMaestro.objects.filter(plan_actual='plus').count()
    maestros_gratis = PerfilMaestro.objects.filter(plan_actual='gratis').count()
    ingresos_plus = maestros_plus * 9990
    
    clientes_premium = PerfilCliente.objects.filter(plan_actual='premium').count()
    clientes_gratis = PerfilCliente.objects.filter(plan_actual='gratis').count()
    ingresos_premium = clientes_premium * 6990

    # Planes SOLO de este mes
    maestros_plus_mes = PerfilMaestro.objects.filter(plan_actual='plus', usuario__date_joined__year=now.year, usuario__date_joined__month=now.month).count()
    ingresos_plus_mes = maestros_plus_mes * 9990
    
    clientes_premium_mes = PerfilCliente.objects.filter(plan_actual='premium', usuario__date_joined__year=now.year, usuario__date_joined__month=now.month).count()
    ingresos_premium_mes = clientes_premium_mes * 6990

    # =========================================================
    # NUEVOS KPIs: Planes SOLO de HOY
    # =========================================================
    maestros_plus_hoy = PerfilMaestro.objects.filter(
        plan_actual='plus', 
        usuario__date_joined__year=now.year, 
        usuario__date_joined__month=now.month, 
        usuario__date_joined__day=now.day
    ).count()
    ingresos_plus_hoy = maestros_plus_hoy * 9990

    clientes_premium_hoy = PerfilCliente.objects.filter(
        plan_actual='premium', 
        usuario__date_joined__year=now.year, 
        usuario__date_joined__month=now.month, 
        usuario__date_joined__day=now.day
    ).count()
    ingresos_premium_hoy = clientes_premium_hoy * 6990

    # Banners totales
    suma_banners = BannerDestacado.objects.aggregate(total=Sum('monto_pagado'))['total']
    ingresos_banners = suma_banners if suma_banners else 0
    
    # Banners SOLO de este mes
    banners_mes_obj = BannerDestacado.objects.exclude(estado='pendiente_pago').filter(fecha_pago__year=now.year, fecha_pago__month=now.month).aggregate(total=Sum('monto_pagado'))['total']
    ingresos_banners_mes = banners_mes_obj if banners_mes_obj else 0

    # Totales sumados
    ingresos_totales = ingresos_tratos + ingresos_plus + ingresos_premium + ingresos_banners
    ingresos_mes_total = ingresos_tratos_mes + ingresos_plus_mes + ingresos_premium_mes + ingresos_banners_mes 

    # --- DATOS PARA GRÁFICO DE OFICIOS ---
    oficios_data = tratos_exitosos.values('servicio__oficio').annotate(total=Count('id')).order_by('-total')
    nombres_oficios = [item['servicio__oficio'] for item in oficios_data]
    cantidades_oficios = [item['total'] for item in oficios_data]

    # DATOS PARA LOS GRÁFICOS DE LÍNEAS
    fecha_inicio_maestros = now - timedelta(days=30)
    maestros_diarios = PerfilMaestro.objects.filter(usuario__date_joined__gte=fecha_inicio_maestros) \
        .annotate(dia=TruncDay('usuario__date_joined')) \
        .values('dia').annotate(total=Count('id')).order_by('dia')
    
    fechas_maestros = [item['dia'].strftime('%d/%m') for item in maestros_diarios if item['dia']]
    cantidades_maestros_linea = [item['total'] for item in maestros_diarios if item['dia']]

    clientes_mensuales = PerfilCliente.objects.annotate(mes=TruncMonth('usuario__date_joined')) \
        .values('mes').annotate(total=Count('id')).order_by('mes')
    
    meses_clientes = [item['mes'].strftime('%m/%Y') for item in clientes_mensuales if item['mes']]
    cantidades_clientes_linea = [item['total'] for item in clientes_mensuales if item['mes']]

    # Ganancias mensuales (Últimos 6 meses asegurados)
    banners_por_mes = BannerDestacado.objects.exclude(estado='pendiente_pago').annotate(mes=TruncMonth('fecha_pago')).values('mes').annotate(total=Sum('monto_pagado'))
    maestros_plus_historial = PerfilMaestro.objects.filter(plan_actual='plus').annotate(mes=TruncMonth('usuario__date_joined')).values('mes').annotate(total=Count('id'))
    clientes_premium_historial = PerfilCliente.objects.filter(plan_actual='premium').annotate(mes=TruncMonth('usuario__date_joined')).values('mes').annotate(total=Count('id'))

    ganancias_dict = {}
    
    for key, val in ganancias_tratos_dict.items():
        ganancias_dict[key] = ganancias_dict.get(key, 0) + val
            
    for b in banners_por_mes:
        if b['mes']: ganancias_dict[(b['mes'].year, b['mes'].month)] = ganancias_dict.get((b['mes'].year, b['mes'].month), 0) + (b['total'] or 0)

    for m in maestros_plus_historial:
        if m['mes']: ganancias_dict[(m['mes'].year, m['mes'].month)] = ganancias_dict.get((m['mes'].year, m['mes'].month), 0) + (m['total'] * 9990)

    for c in clientes_premium_historial:
        if c['mes']: ganancias_dict[(c['mes'].year, c['mes'].month)] = ganancias_dict.get((c['mes'].year, c['mes'].month), 0) + (c['total'] * 6990)
            
    labels_ganancias = []
    datos_ganancias = []
    for i in range(5, -1, -1):
        mes = (now.month - i - 1) % 12 + 1
        anio = now.year + ((now.month - i - 1) // 12)
        labels_ganancias.append(f"{mes:02d}/{anio}")
        datos_ganancias.append(ganancias_dict.get((anio, mes), 0))

    todos_maestros = PerfilMaestro.objects.select_related('usuario').all()
    maestros_estado = [{'perfil': m, 'completo': bool(m.usuario.foto_perfil and m.telefono and m.comuna and m.descripcion and m.oficio_principal)} for m in todos_maestros]
    
    todos_clientes = PerfilCliente.objects.select_related('usuario').all()
    clientes_estado = [{'perfil': c, 'completo': bool(c.usuario.foto_perfil and c.telefono and c.comuna)} for c in todos_clientes]
    
    try:
        visitas_totales = ContadorVisitas.objects.get(id=1).visitas
    except ContadorVisitas.DoesNotExist:
        visitas_totales = 0

    banners_pendientes = BannerDestacado.objects.filter(estado='en_diseno').order_by('fecha_pago')
    banners_activos = BannerDestacado.objects.filter(estado='activo', fecha_expiracion__gt=now).order_by('posicion')

    context = {
        'tratos_exitosos': tratos_exitosos.count(),
        'ingresos_tratos': ingresos_tratos,
        'maestros_plus': maestros_plus,
        'maestros_gratis': maestros_gratis,
        'clientes_premium': clientes_premium,
        'clientes_gratis': clientes_gratis,
        'ingresos_plus': ingresos_plus,
        'ingresos_totales': ingresos_totales,
        'ingresos_mes_total': ingresos_mes_total,
        'ingresos_banners': ingresos_banners,
        'nombres_oficios': nombres_oficios,
        'cantidades_oficios': cantidades_oficios,
        'maestros_estado': maestros_estado,
        'clientes_estado': clientes_estado,
        'visitas_totales': visitas_totales,
        'banners_pendientes': banners_pendientes,
        'banners_activos': banners_activos,
        'fechas_maestros': fechas_maestros,
        'cantidades_maestros_linea': cantidades_maestros_linea,
        'meses_clientes': meses_clientes,
        'cantidades_clientes_linea': cantidades_clientes_linea,
        'labels_ganancias': labels_ganancias,
        'datos_ganancias': datos_ganancias,
        'tratos_hoy_count': tratos_hoy_count,
        'ingresos_tratos_hoy': ingresos_tratos_hoy,
        'maestros_plus_hoy': maestros_plus_hoy,
        'ingresos_plus_hoy': ingresos_plus_hoy,
        'clientes_premium_hoy': clientes_premium_hoy,
        'ingresos_premium_hoy': ingresos_premium_hoy,
    }
    return render(request, 'usuarios/panel_admin.html', context)


def detalle_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCliente, id=solicitud_id)
    return render(request, 'usuarios/detalle_solicitud.html', {'solicitud': solicitud})

@login_required
def editar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCliente, id=solicitud_id, cliente=request.user.perfil_cliente)
    
    if request.method == 'POST':
        solicitud.titulo = request.POST.get('titulo')
        solicitud.descripcion = request.POST.get('descripcion')
        solicitud.oficio_requerido = request.POST.get('oficio')
        solicitud.save()
        
        archivos = request.FILES.getlist('archivos')
        if archivos:
            for archivo in archivos:
                ArchivoSolicitud.objects.create(solicitud=solicitud, archivo=archivo)
                
        messages.success(request, 'Tu solicitud fue actualizada correctamente.')
        return redirect('mi_perfil')
        
    return render(request, 'usuarios/editar_solicitud.html', {
        'solicitud': solicitud,
        'oficios': LISTA_OFICIOS[1:]
    })

@login_required
def toggle_like(request, servicio_id):
    if request.method == 'POST':
        servicio = get_object_or_404(Servicio, id=servicio_id)
        
        if request.user in servicio.likes.all():
            servicio.likes.remove(request.user)
            liked = False
        else:
            servicio.likes.add(request.user)
            liked = True
            
            if request.user != servicio.maestro.usuario:
                nombre_usuario = request.user.first_name if request.user.first_name else request.user.username
                Notificacion.objects.create(
                    usuario=servicio.maestro.usuario,
                    mensaje=f"A {nombre_usuario} le ha gustado tu servicio '{servicio.titulo}'.",
                    enlace=reverse('mi_perfil') 
                )
                
        return JsonResponse({'liked': liked, 'total_likes': servicio.likes.count()})
    return JsonResponse({'error': 'Método no permitido'}, status=405)

@login_required
def eliminar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCliente, id=solicitud_id, cliente=request.user.perfil_cliente)
    
    if request.method == 'POST':
        solicitud.delete()
        
    return redirect('mi_perfil')

@login_required
def evaluar_trato(request, trato_id):
    # Verificamos que el trato exista, pertenezca al cliente logueado y esté finalizado
    trato = get_object_or_404(Trato, id=trato_id, cliente=request.user)
    
    if trato.estado != 'finalizado':
        messages.error(request, 'Solo puedes evaluar trabajos que ya están finalizados.')
        return redirect('mis_trabajos') # Cambia esto si tu url de mis trabajos se llama distinto
        
    if trato.evaluado:
        messages.error(request, 'Ya has evaluado este trato anteriormente.')
        return redirect('mis_trabajos')

    if request.method == 'POST':
        calificacion = request.POST.get('calificacion')
        comentario = request.POST.get('comentario', '')
        imagen_1 = request.FILES.get('imagen_1')
        imagen_2 = request.FILES.get('imagen_2')
        imagen_3 = request.FILES.get('imagen_3')

        if calificacion:
            # Guardamos la reseña
            Resena.objects.create(
                trato=trato,
                maestro=trato.maestro,
                cliente=request.user,
                calificacion=int(calificacion),
                comentario=comentario,
                imagen_1=imagen_1,
                imagen_2=imagen_2,
                imagen_3=imagen_3
            )
            # Marcamos el trato como evaluado
            trato.evaluado = True
            trato.save()
            messages.success(request, '¡Gracias por evaluar al maestro!')
            return redirect('mis_trabajos')

    return render(request, 'usuarios/evaluar_trato.html', {'trato': trato})

@login_required
def ver_resenas(request, username=None):
    if username:
        maestro_user = get_object_or_404(Usuario, username=username, es_maestro=True)
    else:
        maestro_user = request.user

    resenas = Resena.objects.filter(maestro=maestro_user).order_by('-fecha_creacion')
    # Calculamos el promedio de estrellas
    promedio = resenas.aggregate(Avg('calificacion'))['calificacion__avg'] or 0

    return render(request, 'usuarios/ver_resenas.html', {
        'maestro_user': maestro_user,
        'resenas': resenas,
        'promedio': round(promedio, 1)
    })


@login_required
def eliminar_chat(request, contacto_username, servicio_id):
    contacto = get_object_or_404(Usuario, username=contacto_username)
    servicio = get_object_or_404(Servicio, id=servicio_id)

    # Eliminamos el historial usando tu modelo MensajeDirecto y los campos correctos
    MensajeDirecto.objects.filter(
        (Q(remitente=request.user, destinatario=contacto) | Q(remitente=contacto, destinatario=request.user)),
        servicio=servicio
    ).delete()

    return redirect('mensajes')

@login_required
def mis_compras(request):
    # Si es cliente, vemos los tratos donde él es el cliente
    if request.user.es_cliente:
        compras = Trato.objects.filter(cliente=request.user).order_by('-id')
    # Si es maestro, vemos los tratos hechos sobre sus servicios
    elif request.user.es_maestro:
        compras = Trato.objects.filter(servicio__maestro__usuario=request.user).order_by('-id')
    else:
        compras = []

    return render(request, 'usuarios/mis_compras.html', {'compras': compras})

@login_required
def ajustes(request):
    # Vista temporal para que el botón "Ajustes" no genere error
    return render(request, 'usuarios/ajustes.html')