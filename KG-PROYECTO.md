# KG — Krino Guru · Plataforma de Diagnóstico y Conversión con IA

> Documento de referencia del proyecto · Versión 1.0 · Marzo 2026  
> Autor: Isai · Desarrollado con Claude (Anthropic)

---

## ¿Qué es KG?

KG es una plataforma SaaS white-label de diagnóstico y conversión con IA. Permite a empresas de distintos sectores capturar leads calificados mediante formularios de diagnóstico inteligentes que generan recomendaciones personalizadas al instante.

**El concepto central:** el cliente responde preguntas → la IA cruza su perfil con el catálogo del negocio → genera una recomendación personalizada → el cliente agenda una cita → el negocio recibe un lead calificado.

**Inspiración filosófica:** el nombre viene del griego *diakrino* (διακρίνω) — distinguir, discernir, separar lo correcto de lo incorrecto. Como el método socrático: llegar a la verdad a través de las preguntas correctas.

---

## Estado actual del proyecto

| Componente | Estado |
|---|---|
| Módulo de estéticas (demo genérico) | ✅ En producción |
| Formulario multipaso con diseño doodle | ✅ Listo |
| Generación de recomendación con 3 modelos IA | ✅ Funcionando |
| Formulario de cita con envío de correo | ✅ Funcionando |
| Landing page `esteticas.enmerida.mx` | ✅ Lista |
| Sistema multi-tenant | 🔄 En desarrollo |
| Módulo de nutrición | 📋 Pendiente |
| Módulo de bienes raíces | 📋 Pendiente |

---

## Infraestructura

### Repositorios GitHub
- `carvajal-metodo` — cliente Carvajal (no tocar)
- `kg-esteticas` — plataforma KG, módulo de estéticas

### Servicios Railway
- Servicio 1: `carvajal-metodo` → `metodo.centrocarvajal.com`
- Servicio 2: `kg-esteticas` → `*.enmerida.mx`

### Dominios
- `enmerida.mx` — dominio principal en Cloudflare
- `esteticas.enmerida.mx` — módulo de estéticas (activo)
- `metodo.centrocarvajal.com` — cliente Carvajal (activo)

### DNS (Cloudflare)
- Wildcard `*.enmerida.mx` apunta a Railway via CNAME (proxy OFF/gris)
- Cada subdominio nuevo se agrega en Railway como custom domain

---

## Variables de entorno por servicio

### Variables comunes (todos los servicios)
```
CLAUDE_KEY          API key de Anthropic
GEMINI_KEY          API key de Google Gemini
GROQ_KEY            API key de Groq
RESEND_KEY          API key de Resend (cuenta por dominio)
MAIL_FROM           Correo remitente verificado en Resend
MAIL_TO             Correo destino de notificaciones
DEMO_MAIL           Correo destino de solicitudes de cita del demo
BASE_URL            URL base del servicio (ej: esteticas.enmerida.mx)
```

### Variables adicionales (módulo Carvajal)
```
MAIL_CC             Correo con copia en correos de Carvajal
ADMIN_PASSWORD      Contraseña del panel /planes
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
PDFSHIFT_KEY
```

### Nota importante sobre Resend
Cada dominio de envío (`@enmerida.mx`, `@centrocarvajal.com`) requiere:
1. Cuenta Resend separada o dominio verificado en la misma cuenta
2. Registros DNS TXT/CNAME verificados en Cloudflare
3. API key propia en la variable `RESEND_KEY`

---

## Arquitectura del sistema

```
Cliente (browser)
    ↓
Formulario multipaso (formulario-estetica-v2.html)
    ↓
Flask backend (app.py)
    ├── /                    → Landing page
    ├── /demo                → Formulario de diagnóstico
    ├── /demo/recomendar     → Proxy IA (Claude/Gemini/Groq)
    └── /demo/cita           → Envío de correo con Resend
    ↓
IA seleccionada por el usuario
    ↓
Recomendación personalizada en pantalla
    ↓
Formulario de cita → Correo al negocio
```

---

## Modelos de IA integrados

| Modelo | Provider | Uso en demo | Características |
|---|---|---|---|
| `claude-haiku-4-5-20251001` | Anthropic | Recomendación estética | Profundo, detallado |
| `gemini-2.5-flash-lite` | Google | Recomendación estética | Rápido, preciso |
| `llama-3.3-70b-versatile` | Groq | Recomendación estética | Ultrarrápido, detallado |

### System prompt base (demo estéticas)
El prompt instruye a la IA a:
- Hablar directamente al cliente por su nombre usando "tú"
- Tono profesional pero humano — no robótico, no demasiado informal
- Evitar frases genéricas y exclamaciones excesivas
- Demostrar que leyó el perfil específico del cliente
- Estructura: apertura personalizada → justificación → lista de tratamientos → invitación a agendar
- Groq tiene prompt extendido con más detalle (hasta 450 palabras)
- Respuesta en HTML simple: solo `<p>`, `<strong>`, `<ul>`, `<li>`

---

## Flujo del formulario (5 pasos)

### Paso 1 — Perfil básico
- Nombre completo
- Rango de edad (18-25 / 26-35 / 36-45 / 46-55 / 55+)
- Género (Mujer / Hombre)
- Si es mujer: ¿embarazada o lactando?

### Paso 2 — Áreas de interés
- Selección de hasta 2 áreas: Rostro / Cuerpo / Piel / Depilación / Capilar

### Paso 3 — Detalles (condicional según Paso 2)
- **Rostro:** problemas específicos + tono de piel
- **Cuerpo:** zona corporal + objetivos
- **Depilación:** zonas a tratar
- **Piel:** preocupaciones específicas
- **Capilar:** situación capilar
- Campo libre: mayor preocupación (opcional)

### Paso 4 — Hábitos
- Tratamientos estéticos previos (condicional)
- Actividad física
- Nivel de estrés (slider 1-10)
- Urgencia de resultados
- Presupuesto mensual

### Paso 5 — Contacto
- Correo electrónico (requerido)
- WhatsApp (opcional)
- Cómo nos conoció
- Selección de modelo IA

### Pantalla de resultado
- Evaluación personalizada generada por la IA
- Badge del modelo usado
- Formulario de cita (fecha + horario + nota)
- Correo automático al negocio al agendar

---

## Datos que llegan al correo de cita

El correo se envía desde `MAIL_FROM` a `DEMO_MAIL` con asunto:
`Nueva solicitud de cita para — {nombre_paciente}`

Incluye:
- Datos del paciente: nombre, email, WhatsApp, edad, género, embarazo/lactancia, cómo conoció
- Perfil estético: áreas, problemas faciales, tono de piel, zonas corporales, objetivos, zonas depilación, capilar, tratamientos previos, preocupación principal
- Hábitos: actividad física, estrés, urgencia, presupuesto
- Cita: fecha solicitada, horario preferido, nota adicional

---

## Proceso de onboarding de un cliente nuevo

**Lo que el cliente entrega:**
- Lista de tratamientos o servicios
- Fichas técnicas (PDF, Word, PPT — cualquier formato, cualquier idioma)
- Información de su web o brochure
- Precios por tratamiento
- Logo
- Colores principales (hex o referencia)

**Lo que se hace con esa información:**
1. Claude procesa las fichas técnicas y genera fichas estandarizadas
2. Se construye el Excel con 24 columnas por tratamiento (mismo formato que Carvajal)
3. El Excel se convierte a bloque de texto para el prompt
4. Se crea `config.json` con nombre, colores y configuración del tenant
5. Se sube al repo en `tenants/nombre_cliente/`
6. Se agrega el subdominio en Railway y Cloudflare

**Tiempo estimado:** 1-2 horas por cliente nuevo

---

## Estructura de archivos del repo kg-esteticas

```
kg-esteticas/
├── app.py                      # Backend Flask principal
├── formulario-estetica-v2.html # Formulario con diseño doodle
├── formulario-estetica-v1.html # Versión anterior (mantener por referencia)
├── index.html                  # Landing page (esteticas.enmerida.mx/)
├── formulario.html             # Formulario Carvajal (depurar)
├── planes.html                 # Panel de planes Carvajal (depurar)
├── plantilla_plan.html         # Plantilla plan Carvajal (depurar)
├── plantilla_borrador.html     # Borrador Carvajal (depurar)
├── prompt_carvajal.txt         # Prompt Carvajal (depurar)
├── subir_word.html             # Suba word Carvajal (depurar)
├── render.yaml                 # Config Railway
├── requirements.txt            # Dependencias Python
└── tenants/                    # (por crear) Config por cliente
    └── esteticas/
        ├── config.json
        ├── catalogo.txt
        └── prompt.txt
```

### Archivos a depurar (heredados de Carvajal, no necesarios en KG)
- `formulario.html` — formulario de 11 pasos de Carvajal
- `planes.html` — panel de planes de Carvajal
- `plantilla_plan.html` — plantilla del plan de 5 pilares
- `plantilla_borrador.html` — borrador editable
- `prompt_carvajal.txt` — prompt específico de Carvajal
- `subir_word.html` — subida de Word de Carvajal
- Rutas en `app.py`: `/formulario`, `/enviar`, `/planes`, `/status`, `/borrador`

---

## Modelo de negocio

### Tipo de producto
SaaS white-label B2B — se vende a empresas, clínicas y negocios

### Modelo de ventas
- Ventas asistidas (WhatsApp + meetings)
- Demo en vivo personalizado durante la venta
- Setup manual por el equipo (1-2 horas por cliente)
- Sin auto-registro del cliente

### Pricing tentativo
| Plan | Precio mensual | Setup | Incluye |
|---|---|---|---|
| Básico | $80-100 USD | $200 USD | Formulario estándar, recomendaciones genéricas, correo de cita |
| Premium | $150-250 USD | $300-500 USD | Catálogo propio, colores y logo, recomendaciones con tratamientos reales y precios |

### BYOK (Bring Your Own Key)
El cliente usa su propia API key de Claude/Gemini/Groq. El costo de tokens va directo a su cuenta. KG cobra la mensualidad limpia sin margen sobre tokens.

---

## Sectores objetivo

### Alta prioridad (MVP)
- Estéticas y medicina estética ✅ (ya construido)
- Nutrición y planes alimenticios (próximo módulo)

### Media prioridad
- Bienes raíces — diagnóstico de zona ideal para rentar/comprar en Mérida
- Seguros de salud y vida
- Odontología
- Psicología — qué tipo de terapia necesito
- Educación superior — qué carrera o posgrado

### Consideraciones por sector
- **Seguros:** no vende pólizas, genera leads para agentes. Requiere claridad legal
- **Bienes raíces:** requiere base de datos de colonias con atributos reales
- **Medicina:** evitar diagnóstico clínico, solo orientación hacia especialista

---

## Dominios y expansión

### Estrategia actual (local Mérida)
```
enmerida.mx              → raíz (landing del proyecto)
esteticas.enmerida.mx    → módulo estéticas ✅
nutricion.enmerida.mx    → módulo nutrición (próximo)
bienes-raices.enmerida.mx → módulo inmobiliario (futuro)
```

### Estrategia global (cuando se defina el nombre)
```
[nombre].ai              → dominio global del producto
[cliente].enmerida.mx    → clientes locales sin web propia
[cliente].[nombre].ai    → clientes con subdominio propio
```

---

## Diseño del formulario

### Estilo visual — Doodle/Sketch
- **Tipografía:** Caveat (handwritten, títulos) + Nunito (cuerpo)
- **Paleta:** pastel — rosa `#fbb6ce`, azul `#90cdf4`, menta `#9ae6b4`, lavanda `#d6bcfa`, durazno `#fbd38d`
- **Bordes:** `2.5px solid var(--dark)` con `box-shadow: Xpx Xpx 0 var(--dark)` — efecto dibujado a mano
- **Fondo:** blobs SVG orgánicos en las esquinas
- **Cards:** bordes redondeados `border-radius: 16-24px`, elemento decorativo en esquina superior derecha
- **Interacciones:** elementos seleccionados "saltan" con `transform: translateY(-1px)` y sombra más pronunciada

### Referencia
Inspirado en presentaciones estilo doodle/sketch profesional con ilustraciones tipo "muñequitos" — colores pastel, formas orgánicas, tipografía expresiva.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python / Flask |
| Servidor | Gunicorn (gthread) |
| Deploy | Railway |
| Control de versiones | GitHub |
| DNS / CDN | Cloudflare |
| IA — Claude | Anthropic API |
| IA — Gemini | Google Generative AI API |
| IA — Llama | Groq API |
| Correos | Resend |
| Almacenamiento (Carvajal) | Cloudinary |
| Documentos (Carvajal) | python-docx |

### requirements.txt
```
flask==3.0.3
gunicorn==22.0.0
requests==2.32.3
python-docx==1.1.2
resend==2.4.0
cloudinary==1.41.0
openpyxl
```

---

## Rutas activas en kg-esteticas

| Ruta | Método | Descripción |
|---|---|---|
| `/` | GET | Landing page del producto |
| `/demo` | GET | Formulario de diagnóstico estético |
| `/demo/recomendar` | POST | Proxy IA — genera recomendación |
| `/demo/cita` | POST | Envía correo de solicitud de cita |

### Rutas heredadas de Carvajal (a depurar)
`/formulario`, `/enviar`, `/status`, `/planes`, `/borrador`, `/subir-word`, `/admin`

---

## Próximos pasos prioritarios

1. **Depurar `app.py`** — eliminar rutas y código de Carvajal que no aplican a KG
2. **Activar landing page** — que `esteticas.enmerida.mx/` muestre la landing en lugar del index de Carvajal
3. **Multi-tenant básico** — carpeta `tenants/` con config por cliente, Flask detecta subdominio
4. **Módulo nutrición** — formulario adaptado, prompt especializado, catálogo de planes
5. **Definir nombre global** — registrar dominio `.ai` cuando se decida el nombre
6. **Segundo cliente** — primer cliente de pago fuera de Carvajal para validar el modelo

---

## Notas de desarrollo importantes

### Sobre el prompt de recomendación
- Siempre en HTML simple: solo `<p>`, `<strong>`, `<ul>`, `<li>`
- Los `<li>` se renderizan como tarjetas azules con ícono ✨ — el nombre del tratamiento va en `<strong>` al inicio del `<li>` para mostrarse arriba
- Groq tiene prompt extendido con más detalle y hasta 450 palabras
- El tono debe ser profesional pero humano — evitar exclamaciones, frases genéricas y lenguaje clínico frío

### Sobre Resend
- Un dominio = una verificación en Resend
- No se puede enviar desde un dominio no verificado
- Para escalar: considerar un dominio de envío único (`notificaciones@kg-plataforma.com`) para evitar verificar por cliente

### Sobre Railway y Cloudflare
- Wildcard `*.enmerida.mx` en Cloudflare debe tener proxy **OFF** (nube gris)
- Cada subdominio nuevo se agrega en Railway → Settings → Networking → Add Custom Domain
- Railway genera SSL automáticamente para cada dominio

### Sobre el Excel de catálogo (formato Carvajal)
24 columnas por tratamiento:
`ID, Nombre, Categoría, Tipo, Nivel complejidad, Nivel ticket, Problemas principales, Zonas tratables, Grado recomendado, Equipo principal, Equipos complementarios, Tipo energía, Profundidad acción, Tejido objetivo, Resultado fisiológico, Contraindicaciones, Duración sesión, Sesiones recomendadas, Intervalo, Tiempo recuperación, Duración resultados, Combinaciones sugeridas, No combinar con, Orden recomendado`

---

## Contacto y accesos

| Recurso | URL / Info |
|---|---|
| GitHub kg-esteticas | github.com/lsaijr/kg-esteticas |
| GitHub Carvajal | github.com/lsaijr/carvajal-metodo |
| Demo estéticas | esteticas.enmerida.mx/demo |
| Landing estéticas | esteticas.enmerida.mx |
| Carvajal producción | metodo.centrocarvajal.com |
| Railway | railway.app |
| Cloudflare | dash.cloudflare.com |
| Resend | resend.com |

---

*Documento generado con Claude (Anthropic) · Proyecto KG — Krino Guru · Marzo 2026*
