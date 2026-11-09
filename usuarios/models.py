from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

# ==========================================
# USUARIO PERSONALIZADO
# ==========================================
class Usuario(AbstractUser):
    es_cliente = models.BooleanField(default=False)
    es_maestro = models.BooleanField(default=False)
    rut = models.CharField(max_length=12, blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True)

    def __str__(self):
        return self.username

# ==========================================
# PERFILES
# ==========================================
class PerfilCliente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_cliente')
    telefono = models.CharField(max_length=20, blank=True)
    comuna = models.CharField(max_length=100, blank=True)
    plan_actual = models.CharField(
        max_length=20, 
        choices=[('gratis', 'Gratis'), ('premium', 'Premium')], 
        default='gratis'
    )

    def __str__(self):
        return self.usuario.username

class PerfilMaestro(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_maestro')
    telefono = models.CharField(max_length=20, blank=True)
    comuna = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField(blank=True)
    oficio_principal = models.CharField(max_length=100, blank=True)
    plan_actual = models.CharField(
        max_length=20, 
        choices=[('gratis', 'Gratis'), ('plus', 'Plus')], 
        default='gratis'
    )

    def __str__(self):
        return self.usuario.username

class Certificado(models.Model):
    maestro = models.ForeignKey(PerfilMaestro, on_delete=models.CASCADE, related_name='certificados')
    titulo = models.CharField(max_length=100)
    archivo = models.FileField(upload_to='certificados/')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.maestro.usuario.username}"

# ==========================================
# SERVICIOS
# ==========================================
class Servicio(models.Model):
    maestro = models.ForeignKey(PerfilMaestro, on_delete=models.CASCADE, related_name='servicios')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    oficio = models.CharField(max_length=100)
    precio_base = models.IntegerField(null=True, blank=True)
    imagen_portada = models.ImageField(upload_to='servicios/', blank=True, null=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    # Campo para los likes
    likes = models.ManyToManyField(Usuario, related_name='servicios_likeados', blank=True)

    # ==========================================
    # NUEVO CAMPO JSONB PARA POSTGRESQL
    # ==========================================
    detalles_tecnicos = models.JSONField(default=dict, blank=True, null=True)

    def total_likes(self):
        return self.likes.count()

    def __str__(self):
        return self.titulo

# ==========================================
# SOLICITUDES DE CLIENTES (PLAN PREMIUM)
# ==========================================
class SolicitudCliente(models.Model):
    cliente = models.ForeignKey(PerfilCliente, on_delete=models.CASCADE, related_name='solicitudes')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    oficio_requerido = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.titulo} - {self.cliente.usuario.username}"

class ArchivoSolicitud(models.Model):
    solicitud = models.ForeignKey(SolicitudCliente, on_delete=models.CASCADE, related_name='archivos')
    archivo = models.FileField(upload_to='solicitudes_archivos/')
    
    def __str__(self):
        return f"Archivo para: {self.solicitud.titulo}"

# ==========================================
# INTERACCIONES Y COMUNICACIÓN
# ==========================================
class Comentario(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    texto = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='respuestas')

    def __str__(self):
        return f'Comentario de {self.autor.username} en {self.servicio.titulo}'

class Notificacion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    comentario = models.ForeignKey(Comentario, on_delete=models.CASCADE, null=True, blank=True)
    mensaje = models.CharField(max_length=255)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enlace = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f'Notificación para {self.usuario.username}'

class MensajeDirecto(models.Model):
    remitente = models.ForeignKey(Usuario, related_name='mensajes_enviados', on_delete=models.CASCADE)
    destinatario = models.ForeignKey(Usuario, related_name='mensajes_recibidos', on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)
    es_sistema = models.BooleanField(default=False)
    tipo_sistema = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f'De {self.remitente} a {self.destinatario}'

# ==========================================
# TRATOS Y PAGOS
# ==========================================
class Trato(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente'),
        ('en_espera', 'En espera de pago'),
        ('pagado', 'Pagado'),
        ('en_proceso', 'En proceso'),
        ('pospuesto', 'Pospuesto'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    )
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Usuario, related_name='tratos_como_cliente', on_delete=models.CASCADE)
    maestro = models.ForeignKey(Usuario, related_name='tratos_como_maestro', on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    evaluado = models.BooleanField(default=False)

    def __str__(self):
        return f"Trato: {self.servicio.titulo} - {self.cliente.username}"

# ==========================================
# ESTADÍSTICAS
# ==========================================
class ContadorVisitas(models.Model):
    visitas = models.IntegerField(default=0)

    def __str__(self):
        return f"Visitas totales: {self.visitas}"

class BannerDestacado(models.Model):
    ESTADOS = (
        ('pendiente_pago', 'Pendiente de Pago'),
        ('en_diseno', 'Pagado - En Diseño (Admin)'),
        ('activo', 'Activo en Carrusel'),
        ('expirado', 'Expirado (Oculto)'),
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    dias_contratados = models.IntegerField()
    posicion = models.IntegerField(help_text="Lugar en el carrusel (Ej: 1, 2, 3)")
    foto_referencia = models.ImageField(upload_to='banners_referencia/', blank=True, null=True)
    usar_foto_perfil = models.BooleanField(default=False)
    detalles_diseno = models.TextField(max_length=500, blank=True)
    
    # Guardar el dinero pagado
    monto_pagado = models.IntegerField(default=0)
    
    # Textos para el carrusel
    titulo_banner = models.CharField(max_length=100, blank=True)
    texto_banner = models.TextField(max_length=200, blank=True)
    
    # Control administrativo
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente_pago')
    imagen_final_banner = models.ImageField(upload_to='banners_oficiales/', blank=True, null=True)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    fecha_activacion = models.DateTimeField(blank=True, null=True)
    fecha_expiracion = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.estado == 'activo' and not self.fecha_activacion:
            self.fecha_activacion = timezone.now()
            self.fecha_expiracion = self.fecha_activacion + timedelta(days=self.dias_contratados)
        super().save(*args, **kwargs)

    @property
    def esta_vigente(self):
        if self.estado == 'activo' and self.fecha_expiracion:
            return timezone.now() < self.fecha_expiracion
        return False

# ==========================================
# RESEÑAS Y CALIFICACIONES
# ==========================================
class Resena(models.Model):
    trato = models.OneToOneField(Trato, on_delete=models.CASCADE, related_name='resena')
    maestro = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resenas_recibidas')
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resenas_dadas')
    calificacion = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    comentario = models.TextField(blank=True)
    imagen_1 = models.ImageField(upload_to='resenas/', blank=True, null=True)
    imagen_2 = models.ImageField(upload_to='resenas/', blank=True, null=True)
    imagen_3 = models.ImageField(upload_to='resenas/', blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reseña de {self.cliente.username} a {self.maestro.username} ({self.calificacion} estrellas)"