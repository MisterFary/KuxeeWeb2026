from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==========================================
    # PÁGINAS PRINCIPALES Y AUTENTICACIÓN
    # ==========================================
    path('', views.inicio, name='inicio'),
    path('registro/', views.registrar_usuario, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='inicio'), name='logout'),
    
    # ==========================================
    # BÚSQUEDA Y LISTADOS (Nombres corregidos para evitar errores)
    # ==========================================
    path('maestros/', views.lista_maestros, name='maestros'),
    path('maestros/lista/', views.lista_maestros, name='lista_maestros'), # <-- Agrega esta línea como un "alias"
    path('solicitudes/', views.lista_solicitudes, name='solicitudes'),
    path('planes/', views.planes, name='planes'),
    
    # ==========================================
    # PERFIL Y ACCIONES DEL USUARIO
    # ==========================================
    path('perfil/', views.mi_perfil, name='mi_perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/avatar/', views.actualizar_avatar, name='actualizar_avatar'),
    path('maestro/<str:username>/', views.perfil_publico, name='perfil_publico'),
    
    # Rutas para los botones del perfil (redirigen a "En construcción")
    path('perfil/resenas/', views.en_construccion, name='ver_resenas'),
    path('perfil/likes/', views.en_construccion, name='mis_likes'),
    path('perfil/comentarios/', views.en_construccion, name='mis_comentarios'),
    
    # ==========================================
    # SERVICIOS
    # ==========================================
    path('servicio/nuevo/', views.publicar_servicio, name='publicar_servicio'),
    path('servicio/<int:servicio_id>/', views.detalle_servicio, name='detalle_servicio'),
    path('servicio/<int:servicio_id>/editar/', views.editar_servicio, name='editar_servicio'),
    path('servicio/<int:servicio_id>/eliminar/', views.eliminar_servicio, name='eliminar_servicio'),
    path('servicio/<int:servicio_id>/comentar/', views.agregar_comentario, name='agregar_comentario'),
    path('publicar-solicitud/', views.publicar_solicitud, name='publicar_solicitud'),
    path('solicitud/<int:solicitud_id>/', views.detalle_solicitud, name='detalle_solicitud'),
    path('solicitud/editar/<int:solicitud_id>/', views.editar_solicitud, name='editar_solicitud'),
    path('solicitud/eliminar/<int:solicitud_id>/', views.eliminar_solicitud, name='eliminar_solicitud'),
    path('banner/procesar-pago/', views.procesar_pago_banner, name='procesar_pago_banner'),
    path('banner/pagar/<int:banner_id>/', views.pasarela_pago_banner, name='pasarela_pago_banner'),
    path('servicios/', views.lista_servicios, name='servicios'),
    
    # ==========================================
    # NOTIFICACIONES
    # ==========================================
    path('notificacion/leer/<int:notificacion_id>/', views.leer_notificacion, name='leer_notificacion'),
    path('notificacion/marcar/<int:notificacion_id>/', views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('notificacion/eliminar/<int:notificacion_id>/', views.eliminar_notificacion, name='eliminar_notificacion'),
    path('servicio/<int:servicio_id>/like/', views.toggle_like, name='toggle_like'),
    
    # ==========================================
    # MENSAJERÍA, TRATOS Y PAGOS DE COMISIÓN
    # ==========================================
    path('mensajes/', views.mis_mensajes, name='mensajes'),
    path('mis-trabajos/', views.mis_trabajos, name='mis_trabajos'),
    path('trato/gestionar/', views.gestionar_trato, name='gestionar_trato'),
    path('pasarela/<int:trato_id>/', views.pasarela_pago, name='pasarela_pago'),
    path('guardar_rut/', views.guardar_rut, name='guardar_rut'),
    
    # ==========================================
    # SUSCRIPCIONES (MAESTRO PLUS)
    # ==========================================
    path('suscripcion/', views.pasarela_suscripcion, name='pasarela_suscripcion'),
    path('suscripcion/procesar/', views.procesar_pago_suscripcion, name='procesar_pago_suscripcion'),
    
    # ==========================================
    # OTROS (Páginas de sistema)
    # ==========================================
    path('en-construccion/', views.en_construccion, name='en_construccion'),
    path('acceso-denegado/', views.acceso_denegado, name='acceso_denegado'),

    path('panel-kuxee/', views.panel_admin, name='panel_admin'),

    path('trato/<int:trato_id>/evaluar/', views.evaluar_trato, name='evaluar_trato'),
    path('resenas/', views.ver_resenas, name='ver_resenas'),    
    path('resenas/<str:username>/', views.ver_resenas, name='ver_resenas_publico'),
]