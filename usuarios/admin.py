from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import BannerDestacado
from .models import (
    Usuario, 
    PerfilCliente, 
    PerfilMaestro, 
    Certificado, 
    Servicio, 
    Comentario, 
    Notificacion, 
    MensajeDirecto, 
    Trato,
    ContadorVisitas
)

# ==========================================
# USUARIO PERSONALIZADO
# ==========================================
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Roles e Información de Kuxee', {'fields': ('es_cliente', 'es_maestro', 'rut', 'foto_perfil')}),
    )
    list_display = ('username', 'email', 'first_name', 'es_cliente', 'es_maestro')
    list_filter = ('es_cliente', 'es_maestro', 'is_staff', 'is_active')

# ==========================================
# PERFILES
# ==========================================
@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    # Agregamos plan_actual para verlo y editarlo rápido
    list_display = ('usuario', 'telefono', 'comuna', 'plan_actual')
    list_filter = ('plan_actual', 'comuna')
    search_fields = ('usuario__username', 'comuna')
    list_editable = ('plan_actual',)

@admin.register(PerfilMaestro)
class PerfilMaestroAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'oficio_principal', 'comuna', 'plan_actual')
    list_filter = ('plan_actual', 'oficio_principal')
    search_fields = ('usuario__username', 'comuna', 'oficio_principal')
    list_editable = ('plan_actual',)

# ==========================================
# SERVICIOS Y TRATOS
# ==========================================
@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'maestro', 'oficio', 'precio_base', 'fecha_publicacion')
    list_filter = ('oficio', 'fecha_publicacion')
    search_fields = ('titulo', 'descripcion', 'maestro__usuario__username')

@admin.register(Trato)
class TratoAdmin(admin.ModelAdmin):
    list_display = ('servicio', 'cliente', 'maestro', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('servicio__titulo', 'cliente__username', 'maestro__username')

# ==========================================
# ESTADÍSTICAS
# ==========================================
@admin.register(ContadorVisitas)
class ContadorVisitasAdmin(admin.ModelAdmin):
    list_display = ('id', 'visitas')

# ==========================================
# OTROS MODELOS (Registro simple)
# ==========================================
admin.site.register(Certificado)
admin.site.register(Comentario)
admin.site.register(Notificacion)
admin.site.register(MensajeDirecto)

@admin.register(BannerDestacado)
class BannerDestacadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'dias_contratados', 'posicion', 'estado', 'fecha_expiracion', 'esta_vigente')
    list_filter = ('estado',)
    list_editable = ('estado',)
    readonly_fields = ('fecha_activacion', 'fecha_expiracion')