from django import forms
from django.contrib.auth import get_user_model, password_validation, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.db.models import Q

Usuario = get_user_model()

# 1. LISTA DE REGIONES Y COMUNAS
REGIONES_Y_COMUNAS = [
    ('', 'Selecciona una comuna...'),
    ('Región de Arica y Parinacota', (
        ('arica_parinacota_completa', '📍 Toda la región'), ('arica', 'Arica'), ('camarones', 'Camarones'), ('general_lagos', 'General Lagos'), ('putre', 'Putre'),
    )),
    ('Región de Tarapacá', (
        ('tarapaca_completa', '📍 Toda la región'), ('iquique', 'Iquique'), ('alto_hospicio', 'Alto Hospicio'), ('camina', 'Camiña'), ('colchane', 'Colchane'), ('huara', 'Huara'), ('pica', 'Pica'), ('pozo_almonte', 'Pozo Almonte'),
    )),
    ('Región de Antofagasta', (
        ('antofagasta_completa', '📍 Toda la región'), ('antofagasta', 'Antofagasta'), ('mejillones', 'Mejillones'), ('sierra_gorda', 'Sierra Gorda'), ('taltal', 'Taltal'), ('calama', 'Calama'), ('ollague', 'Ollagüe'), ('san_pedro_de_atacama', 'San Pedro de Atacama'), ('maria_elena', 'María Elena'), ('tocopilla', 'Tocopilla'),
    )),
    ('Región de Atacama', (
        ('atacama_completa', '📍 Toda la región'), ('copiapo', 'Copiapó'), ('caldera', 'Caldera'), ('tierra_amarilla', 'Tierra Amarilla'), ('chanaral', 'Chañaral'), ('diego_de_almagro', 'Diego de Almagro'), ('vallenar', 'Vallenar'), ('alto_del_carmen', 'Alto del Carmen'), ('freirina', 'Freirina'), ('huasco', 'Huasco'),
    )),
    ('Región de Coquimbo', (
        ('coquimbo_completa', '📍 Toda la región'), ('la_serena', 'La Serena'), ('coquimbo', 'Coquimbo'), ('andacollo', 'Andacollo'), ('la_higuera', 'La Higuera'), ('paihuano', 'Paihuano'), ('vicuna', 'Vicuña'), ('illapel', 'Illapel'), ('canela', 'Canela'), ('los_vilos', 'Los Vilos'), ('salamanca', 'Salamanca'), ('ovalle', 'Ovalle'), ('combarbala', 'Combarbalá'), ('monte_patria', 'Monte Patria'), ('punitaqui', 'Punitaqui'), ('rio_hurtado', 'Río Hurtado'),
    )),
    ('Región de Valparaíso', (
        ('valparaiso_completa', '📍 Toda la región'), ('valparaiso', 'Valparaíso'), ('casablanca', 'Casablanca'), ('concon', 'Concón'), ('juan_fernandez', 'Juan Fernández'), ('puchuncavi', 'Puchuncaví'), ('quintero', 'Quintero'), ('vina_del_mar', 'Viña del Mar'), ('isla_de_pascua', 'Isla de Pascua'), ('los_andes', 'Los Andes'), ('calle_larga', 'Calle Larga'), ('rinconada', 'Rinconada'), ('san_esteban', 'San Esteban'), ('la_ligua', 'La Ligua'), ('cabildo', 'Cabildo'), ('papudo', 'Papudo'), ('petorca', 'Petorca'), ('zapallar', 'Zapallar'), ('quillota', 'Quillota'), ('la_calera', 'La Calera'), ('hijuelas', 'Hijuelas'), ('la_cruz', 'La Cruz'), ('nogales', 'Nogales'), ('san_antonio', 'San Antonio'), ('algarrobo', 'Algarrobo'), ('cartagena', 'Cartagena'), ('el_quisco', 'El Quisco'), ('el_tabo', 'El Tabo'), ('santo_domingo', 'Santo Domingo'), ('san_felipe', 'San Felipe'), ('catemu', 'Catemu'), ('llaillay', 'Llaillay'), ('panquehue', 'Panquehue'), ('putaendo', 'Putaendo'), ('santa_maria', 'Santa María'), ('quilpue', 'Quilpué'), ('limache', 'Limache'), ('olmue', 'Olmué'), ('villa_alemana', 'Villa Alemana'),
    )),
    ('Región Metropolitana de Santiago', (
        ('metropolitana_completa', '📍 Toda la región'), ('cerrillos', 'Cerrillos'), ('cerro_navia', 'Cerro Navia'), ('conchali', 'Conchalí'), ('el_bosque', 'El Bosque'), ('estacion_central', 'Estación Central'), ('huechuraba', 'Huechuraba'), ('independencia', 'Independencia'), ('la_cisterna', 'La Cisterna'), ('la_florida', 'La Florida'), ('la_granja', 'La Granja'), ('la_pintana', 'La Pintana'), ('la_reina', 'La Reina'), ('las_condes', 'Las Condes'), ('lo_barnechea', 'Lo Barnechea'), ('lo_espejo', 'Lo Espejo'), ('lo_prado', 'Lo Prado'), ('macul', 'Macul'), ('maipu', 'Maipú'), ('nunoa', 'Ñuñoa'), ('pedro_aguirre_cerda', 'Pedro Aguirre Cerda'), ('penalolen', 'Peñalolén'), ('providencia', 'Providencia'), ('pudahuel', 'Pudahuel'), ('quilicura', 'Quilicura'), ('quinta_normal', 'Quinta Normal'), ('recoleta', 'Recoleta'), ('renca', 'Renca'), ('san_joaquin', 'San Joaquín'), ('san_miguel', 'San Miguel'), ('san_ramon', 'San Ramón'), ('santiago', 'Santiago'), ('vitacura', 'Vitacura'), ('puente_alto', 'Puente Alto'), ('pirque', 'Pirque'), ('san_jose_de_maipo', 'San José de Maipo'), ('colina', 'Colina'), ('lampa', 'Lampa'), ('tiltil', 'Tiltil'), ('san_bernardo', 'San Bernardo'), ('buin', 'Buin'), ('calera_de_tango', 'Calera de Tango'), ('paine', 'Paine'), ('melipilla', 'Melipilla'), ('alhue', 'Alhué'), ('curacavi', 'Curacaví'), ('maria_pinto', 'María Pinto'), ('san_pedro', 'San Pedro'), ('talagante', 'Talagante'), ('el_monte', 'El Monte'), ('isla_de_maipo', 'Isla de Maipo'), ('padre_hurtado', 'Padre Hurtado'), ('penaflor', 'Peñaflor'),
    )),
    ('Región del Libertador Gral. Bernardo O\'Higgins', (
        ('ohiggins_completa', '📍 Toda la región'), ('rancagua', 'Rancagua'), ('codegua', 'Codegua'), ('coinco', 'Coinco'), ('coltauco', 'Coltauco'), ('donihue', 'Doñihue'), ('graneros', 'Graneros'), ('las_cabras', 'Las Cabras'), ('machali', 'Machalí'), ('malloa', 'Malloa'), ('mostazal', 'Mostazal'), ('olivar', 'Olivar'), ('peumo', 'Peumo'), ('pichidegua', 'Pichidegua'), ('quinta_de_tilcoco', 'Quinta de Tilcoco'), ('rengo', 'Rengo'), ('requinoa', 'Requínoa'), ('san_vicente', 'San Vicente'), ('pichilemu', 'Pichilemu'), ('la_estrella', 'La Estrella'), ('litueche', 'Litueche'), ('marchihue', 'Marchihue'), ('navidad', 'Navidad'), ('paredones', 'Paredones'), ('san_fernando', 'San Fernando'), ('chepica', 'Chépica'), ('chimbarongo', 'Chimbarongo'), ('lolol', 'Lolol'), ('nancagua', 'Nancagua'), ('palmilla', 'Palmilla'), ('peralillo', 'Peralillo'), ('placilla', 'Placilla'), ('pumanque', 'Pumanque'), ('santa_cruz', 'Santa Cruz'),
    )),
    ('Región del Maule', (
        ('maule_completa', '📍 Toda la región'), ('talca', 'Talca'), ('constitucion', 'Constitución'), ('curepto', 'Curepto'), ('empedrado', 'Empedrado'), ('maule', 'Maule'), ('pelarco', 'Pelarco'), ('pencahue', 'Pencahue'), ('rio_claro', 'Río Claro'), ('san_clemente', 'San Clemente'), ('san_rafael', 'San Rafael'), ('cauquenes', 'Cauquenes'), ('chanco', 'Chanco'), ('pelluhue', 'Pelluhue'), ('curico', 'Curicó'), ('hualane', 'Hualañé'), ('licanten', 'Licantén'), ('molina', 'Molina'), ('rauco', 'Rauco'), ('romeral', 'Romeral'), ('sagrada_familia', 'Sagrada Familia'), ('teno', 'Teno'), ('vichuquen', 'Vichuquén'), ('linares', 'Linares'), ('colbun', 'Colbún'), ('longavi', 'Longaví'), ('parral', 'Parral'), ('retiro', 'Retiro'), ('san_javier', 'San Javier'), ('villa_alegre', 'Villa Alegre'), ('yerbas_buenas', 'Yerbas Buenas'),
    )),
    ('Región de Ñuble', (
        ('nuble_completa', '📍 Toda la región'), ('chillan', 'Chillán'), ('bulnes', 'Bulnes'), ('chillan_viejo', 'Chillán Viejo'), ('el_carmen', 'El Carmen'), ('pemuco', 'Pemuco'), ('pinto', 'Pinto'), ('quillon', 'Quillón'), ('san_ignacio', 'San Ignacio'), ('yungay', 'Yungay'), ('quirihue', 'Quirihue'), ('cobquecura', 'Cobquecura'), ('coelemu', 'Coelemu'), ('ninhue', 'Ninhue'), ('portezuelo', 'Portezuelo'), ('ranquil', 'Ránquil'), ('trehuaco', 'Trehuaco'), ('san_carlos', 'San Carlos'), ('coihueco', 'Coihueco'), ('niquen', 'Ñiquén'), ('san_fabian', 'San Fabián'), ('san_nicolas', 'San Nicolás'),
    )),
    ('Región del Biobío', (
        ('biobio_completa', '📍 Toda la región'), ('concepcion', 'Concepción'), ('coronel', 'Coronel'), ('chiguayante', 'Chiguayante'), ('florida', 'Florida'), ('hualpen', 'Hualpén'), ('hualqui', 'Hualqui'), ('lota', 'Lota'), ('penco', 'Penco'), ('san_pedro_de_la_paz', 'San Pedro de la Paz'), ('santa_juana', 'Santa Juana'), ('talcahuano', 'Talcahuano'), ('tome', 'Tomé'), ('lebu', 'Lebu'), ('arauco', 'Arauco'), ('canete', 'Cañete'), ('contulmo', 'Contulmo'), ('curanilahue', 'Curanilahue'), ('los_alamos', 'Los Álamos'), ('tirua', 'Tirúa'), ('los_angeles', 'Los Ángeles'), ('antuco', 'Antuco'), ('cabrero', 'Cabrero'), ('laja', 'Laja'), ('mulchen', 'Mulchén'), ('nacimiento', 'Nacimiento'), ('negrete', 'Negrete'), ('quilaco', 'Quilaco'), ('quilleco', 'Quilleco'), ('san_rosendo', 'San Rosendo'), ('santa_barbara', 'Santa Bárbara'), ('tucapel', 'Tucapel'), ('yumbel', 'Yumbel'), ('alto_biobio', 'Alto Biobío'),
    )),
    ('Región de La Araucanía', (
        ('araucania_completa', '📍 Toda la región'), ('temuco', 'Temuco'), ('carahue', 'Carahue'), ('cholchol', 'Cholchol'), ('cunco', 'Cunco'), ('curarrehue', 'Curarrehue'), ('freire', 'Freire'), ('galvarino', 'Galvarino'), ('gorbea', 'Gorbea'), ('lautaro', 'Lautaro'), ('loncoche', 'Loncoche'), ('melipeuco', 'Melipeuco'), ('nueva_imperial', 'Nueva Imperial'), ('padre_las_casas', 'Padre Las Casas'), ('perquenco', 'Perquenco'), ('pitrufquen', 'Pitrufquén'), ('pucon', 'Pucón'), ('saavedra', 'Saavedra'), ('teodoro_schmidt', 'Teodoro Schmidt'), ('tolten', 'Toltén'), ('vilcun', 'Vilcún'), ('villarrica', 'Villarrica'), ('angol', 'Angol'), ('collipulli', 'Collipulli'), ('curacautin', 'Curacautín'), ('ercilla', 'Ercilla'), ('lonquimay', 'Lonquimay'), ('los_sauces', 'Los Sauces'), ('lumaco', 'Lumaco'), ('puren', 'Purén'), ('renaico', 'Renaico'), ('traiguen', 'Traiguén'), ('victoria', 'Victoria'),
    )),
    ('Región de Los Ríos', (
        ('los_rios_completa', '📍 Toda la región'), ('valdivia', 'Valdivia'), ('corral', 'Corral'), ('lanco', 'Lanco'), ('los_lagos', 'Los Lagos'), ('mafil', 'Máfil'), ('mariquina', 'Mariquina'), ('paillaco', 'Paillaco'), ('panguipulli', 'Panguipulli'), ('la_union', 'La Unión'), ('futrono', 'Futrono'), ('lago_ranco', 'Lago Ranco'), ('rio_bueno', 'Río Bueno'),
    )),
    ('Región de Los Lagos', (
        ('los_lagos_completa', '📍 Toda la región'), ('puerto_montt', 'Puerto Montt'), ('calbuco', 'Calbuco'), ('cochamo', 'Cochamó'), ('fresia', 'Fresia'), ('frutillar', 'Frutillar'), ('los_muermos', 'Los Muermos'), ('llanquihue', 'Llanquihue'), ('maullin', 'Maullín'), ('puerto_varas', 'Puerto Varas'), ('castro', 'Castro'), ('ancud', 'Ancud'), ('chonchi', 'Chonchi'), ('curaco_de_velez', 'Curaco de Vélez'), ('dalcahue', 'Dalcahue'), ('puqueldon', 'Puqueldón'), ('queilen', 'Queilén'), ('quellon', 'Quellón'), ('quemchi', 'Quemchi'), ('quinchao', 'Quinchao'), ('osorno', 'Osorno'), ('puerto_octay', 'Puerto Octay'), ('purranque', 'Purranque'), ('puyehue', 'Puyehue'), ('rio_negro', 'Río Negro'), ('san_juan_de_la_costa', 'San Juan de la Costa'), ('san_pablo', 'San Pablo'), ('chaiten', 'Chaitén'), ('futaleufu', 'Futaleufú'), ('hualaihue', 'Hualaihué'), ('palena', 'Palena'),
    )),
    ('Región de Aysén', (
        ('aysen_completa', '📍 Toda la región'), ('coyhaique', 'Coyhaique'), ('lago_verde', 'Lago Verde'), ('aysen', 'Aysén'), ('cisnes', 'Cisnes'), ('guaitecas', 'Guaitecas'), ('cochrane', 'Cochrane'), ('ohiggins', 'O\'Higgins'), ('tortel', 'Tortel'), ('chile_chico', 'Chile Chico'), ('rio_ibanez', 'Río Ibáñez'),
    )),
    ('Región de Magallanes', (
        ('magallanes_completa', '📍 Toda la región'), ('punta_arenas', 'Punta Arenas'), ('laguna_blanca', 'Laguna Blanca'), ('rio_verde', 'Río Verde'), ('san_gregorio', 'San Gregorio'), ('cabo_de_hornos', 'Cabo de Hornos'), ('antartica', 'Antártica'), ('porvenir', 'Porvenir'), ('primavera', 'Primavera'), ('timaukel', 'Timaukel'), ('natales', 'Natales'), ('torres_del_paine', 'Torres del Paine'),
    )),
]

# 2. LISTA DE OFICIOS AGRUPADOS
LISTA_OFICIOS = [
    ('', 'Selecciona un oficio...'),
    ('Arte y diseño', (
        ('costurero', 'Costurero/a'), ('ilustracion', 'Ilustración'), ('pintura_arte', 'Pintura'), ('tatuaje', 'Tatuaje'), ('diseno_grafico', 'Diseño gráfico'), ('diseno_interiores', 'Diseño de interiores'),
    )),
    ('Belleza y bienestar', (
        ('peluqueria', 'Peluquería'), ('manicure', 'Manicure'), ('pedicure', 'Pedicure'), ('maquillaje', 'Maquillaje'), ('masajes', 'Masajes'), ('depilacion', 'Depilación'),
    )),
    ('Educación', (
        ('profesor_particular', 'Profesor particular'), ('idiomas', 'Idiomas'), ('musica_instrumentos', 'Música / Instrumentos'), ('preuniversitario', 'Preuniversitario'),
    )),
    ('Eventos', (
        ('fotografia', 'Fotografía'), ('video', 'Video'), ('dj_musica', 'DJ / Música'), ('decoracion', 'Decoración'), ('catering', 'Catering'), ('animacion', 'Animación'),
    )),
    ('Hogar y reparaciones', (
        ('gasfiteria', 'Gasfitería'), ('electricidad', 'Electricidad'), ('plomeria', 'Plomería'), ('albanileria', 'Albañilería'), ('pintura_hogar', 'Pintura'), ('carpinteria', 'Carpintería'), ('cerrajeria', 'Cerrajería'), ('jardineria', 'Jardinería'), ('limpieza', 'Limpieza'), ('mudanzas', 'Mudanzas'), ('aire_acondicionado', 'Aire acondicionado'),
    )),
    ('Mascotas', (
        ('paseador', 'Paseador'), ('peluqueria_canina', 'Peluquería canina'), ('cuidado_mascotas', 'Cuidado de mascotas'), ('adiestramiento', 'Adiestramiento'),
    )),
    ('Mecánica y vehículos', (
        ('mecanico', 'Mecánico'), ('lavado_autos', 'Lavado de autos'), ('pintura_automotriz', 'Pintura automotriz'),
    )),
    ('Salud', (
        ('nutricionista', 'Nutricionista'), ('entrenador_personal', 'Entrenador personal'), ('kinesiologo', 'Kinesiólogo'), ('psicologo', 'Psicólogo'), ('enfermeria', 'Enfermería'),
    )),
    ('Servicios profesionales', (
        ('abogado', 'Abogado'), ('contador', 'Contador'), ('asesor_financiero', 'Asesor financiero'), ('traduccion', 'Traducción'),
    )),
    ('Tecnología', (
        ('programador', 'Programador'), ('diseno_web', 'Diseño web'), ('reparacion_pc', 'Reparación PC'), ('reparacion_movil', 'Reparación móvil'), ('redes', 'Redes'), ('marketing_digital', 'Marketing digital'),
    )),
    ('Transporte', (
        ('chofer', 'Chofer'), ('fletes', 'Fletes'), ('delivery', 'Delivery'),
    )),
    ('Otros', (
        ('otro', 'Otro'),
    )),
]


# 3. FORMULARIO DE REGISTRO
class RegistroKuxeeForm(forms.Form):
    first_name = forms.CharField(
        max_length=100,
        label='Nombre completo',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: Juan Pérez', 'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=150,
        label='Nombre de usuario',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: juanperez123', 'class': 'form-control'})
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'placeholder': 'Ej: juan@correo.com', 'class': 'form-control'})
    )
    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Crea una contraseña segura', 'class': 'form-control'})
    )
    repite_contrasena = forms.CharField(
        label='Repite tu contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Repite la contraseña', 'class': 'form-control'})
    )
    telefono = forms.CharField(
        max_length=15,
        label='Teléfono',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: +56912345678', 'class': 'form-control'})
    )

    comunas = forms.MultipleChoiceField(
        choices=REGIONES_Y_COMUNAS,
        label='Comunas',
        required=True,
        widget=forms.SelectMultiple(attrs={'id': 'id_comunas', 'style': 'display: none;'})
    )
    
    # NUEVO: Convertimos a MultipleChoiceField
    oficios = forms.MultipleChoiceField(
        choices=LISTA_OFICIOS,
        label='Oficios',
        required=False,
        widget=forms.SelectMultiple(attrs={'id': 'id_oficios', 'style': 'display: none;'})
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if Usuario.objects.filter(username__iexact=username).exists():
            raise ValidationError("Este usuario ya está registrado.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError("Este correo ya está registrado.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        contrasena = cleaned_data.get("contrasena")
        repite_contrasena = cleaned_data.get("repite_contrasena")
        rol = self.data.get("rol", "cliente")
        oficios = cleaned_data.get("oficios")

        if contrasena and repite_contrasena and contrasena != repite_contrasena:
            raise ValidationError("Las contraseñas no coinciden. Por favor, inténtalo de nuevo.")

        if contrasena:
            try:
                password_validation.validate_password(contrasena)
            except ValidationError as error:
                self.add_error('contrasena', error)

        if rol == 'maestro' and not oficios:
            self.add_error('oficios', 'Debes seleccionar al menos un oficio si te registras como maestro.')

        return cleaned_data


# 4. FORMULARIO DE LOGIN PERSONALIZADO
class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario o Correo electrónico',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: juanperez o juan@correo.com'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ingresa tu contraseña'})
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            
            if self.user_cache is None:
                raise ValidationError("El correo, usuario o contraseña son incorrectos.")
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data