import os, json, uuid, threading, calendar, secrets, hashlib
import cloudinary
import cloudinary.uploader
WEASYPRINT_OK = False
WeasyprintHTML = None
from datetime import date, datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory
import requests as req
import zipfile, re, html as htmllib
app = Flask(__name__)

# ── Config desde variables de entorno ────────────────────────
CLAUDE_KEY  = os.environ.get('CLAUDE_KEY', '')
GEMINI_KEY  = os.environ.get('GEMINI_KEY', '')
GROQ_KEY    = os.environ.get('GROQ_KEY', '')
RESEND_KEY  = os.environ.get('RESEND_KEY', '')
MAIL_CC         = [m.strip() for m in os.environ.get('MAIL_CC','').split(',') if m.strip()]
ADMIN_PASSWORD  = os.environ.get('ADMIN_PASSWORD', 'carvajal2026')
MAIL_TO     = os.environ.get('MAIL_TO', 'isai.josue@gmail.com').strip()
MAIL_FROM   = os.environ.get('MAIL_FROM', 'envios@centrocarvajal.com')
DEMO_MAIL   = os.environ.get('DEMO_MAIL', 'isai.josue@gmail.com')
PLANES_DIR  = os.path.join(os.path.dirname(__file__), 'planes_generados')
os.makedirs(PLANES_DIR, exist_ok=True)

# ── Cloudinary ────────────────────────────────────────────────
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_API_KEY    = os.environ.get('CLOUDINARY_API_KEY', '')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')
if CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name = CLOUDINARY_CLOUD_NAME,
        api_key    = CLOUDINARY_API_KEY,
        api_secret = CLOUDINARY_API_SECRET,
        secure     = True
    )

# ── Jobs en memoria ───────────────────────────────────────────
jobs = {}  # jobId -> {'status': ..., 'msg': ..., 'html_url': ...}
admin_tokens = set()  # tokens de sesión activos

# ════════════════════════════════════════════════════════════
# RUTAS
# ════════════════════════════════════════════════════════════

@app.route('/', methods=['GET'])
def index():
    with open(os.path.join(os.path.dirname(__file__), 'index.html'), encoding='utf-8') as f:
        return f.read()

# ── Demo — formulario estético simplificado ──────────────────
@app.route('/demo')
def demo():
    with open(os.path.join(os.path.dirname(__file__), 'formulario-estetica-v2.html'), encoding='utf-8') as f:
        return f.read()

@app.route('/demo/recomendar', methods=['POST'])
def demo_recomendar():
    """Proxy multi-modelo para el formulario demo — las keys nunca salen del servidor."""
    try:
        data   = request.get_json(force=True)
        perfil = data.get('perfil', '')
        modelo = data.get('modelo', 'claude')
        if not perfil:
            return jsonify({'error': 'Sin datos de perfil'}), 400

        base_prompt = (
            'Eres una especialista en estética con años de experiencia. Tu forma de comunicarte es cálida, respetuosa y genuinamente personalizada. '
            'Le hablas al cliente por su nombre y usas "tú". '
            'TONO: profesional pero humano — como una especialista que realmente leyó su caso y le habla con consideración, no como un robot generando texto genérico ni como una amiga informal. '
            'EVITA absolutamente: frases genéricas como "¡Hola!", exclamaciones excesivas, emojis en el texto, frases vacías como "es un placer atenderte", lenguaje clínico frío, o recomendaciones que podrían ser para cualquier persona. '
            'BUSCA: oraciones que demuestren que leíste el perfil específico del cliente — menciona su situación real, sus áreas de interés, su nivel de estrés o actividad física cuando sea relevante. Que cada frase aporte algo concreto. '
            'Responde SIEMPRE en HTML simple usando solo estas etiquetas: <p>, <strong>, <ul>, <li>. '
            'NO uses markdown, NO uses asteriscos (**), NO uses encabezados, NO uses tablas. '
            'Para resaltar el nombre de un tratamiento usa ÚNICAMENTE la etiqueta HTML <strong>, nunca asteriscos. '
            'Estructura: '
            '1. Abre mencionando el nombre del cliente y una observación específica sobre su perfil que demuestre que lo leíste — algo como reconocer su preocupación principal o su situación particular. '
            '2. Explica brevemente por qué los tratamientos que vas a recomendar tienen sentido para SU caso específico, en lenguaje claro sin tecnicismos. '
            '3. Lista los tratamientos recomendados — nombre del tratamiento en negrita y una frase concreta sobre qué resultado puede esperar esta persona en particular. '
            '4. Cierra con una invitación a agendar su consulta, transmitiendo que en ese espacio podrán profundizar y resolver todas sus dudas.'
        )

        if modelo == 'groq':
            sys_prompt = base_prompt + (
                ' IMPORTANTE: sé detallada y muy personalizada, pero mantén un tono cercano y natural — nada de lenguaje corporativo ni frases de manual. '
                'Integra datos reales del perfil de forma orgánica en el texto: edad, nivel de estrés, actividad física, historial de tratamientos. '
                'No menciones el presupuesto bajo ningún concepto — ni directa ni indirectamente. Nunca uses frases como "considerando tu presupuesto", "dentro de tus posibilidades", "limitaciones económicas" o similares. '
                'Evita completamente frases hechas como "¿te gustaría explorar estas opciones?", "no dudes en contactarnos", "estamos a tu disposición", "el mejor curso de acción". '
                'Cada tratamiento merece 2-3 oraciones — qué hace, por qué encaja específicamente con este perfil y qué resultado concreto puede esperar esta persona. '
                'Cierra con una sola oración natural invitando a agendar, sin preguntas retóricas. '
                'Máximo 450 palabras.'
            )
        else:
            sys_prompt = base_prompt + ' Máximo 300 palabras. Cada frase debe aportar valor concreto — nada de relleno.'

        user_msg = 'Perfil del paciente:\n' + perfil

        # ── Claude ──────────────────────────────────────────
        if modelo == 'claude':
            r = req.post('https://api.anthropic.com/v1/messages',
                headers={'Content-Type':'application/json','x-api-key':CLAUDE_KEY,'anthropic-version':'2023-06-01'},
                json={'model':'claude-haiku-4-5-20251001','max_tokens':800,
                      'system':sys_prompt,'messages':[{'role':'user','content':user_msg}]},
                timeout=30)
            j = r.json()
            if 'content' in j and j['content']:
                return jsonify({'html': j['content'][0]['text']})
            return jsonify({'error': 'Sin respuesta de Claude', 'detail': j}), 500

        # ── Gemini ──────────────────────────────────────────
        elif modelo == 'gemini':
            url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}'
            r = req.post(url,
                headers={'Content-Type':'application/json'},
                json={'system_instruction':{'parts':[{'text':sys_prompt}]},
                      'contents':[{'parts':[{'text':user_msg}]}],
                      'generationConfig':{'maxOutputTokens':800}},
                timeout=30)
            j = r.json()
            print(f'[demo/gemini] status={r.status_code} response={json.dumps(j)[:300]}')
            if 'candidates' in j and j['candidates']:
                return jsonify({'html': j['candidates'][0]['content']['parts'][0]['text']})
            # Devolver el error completo al frontend para debug
            error_msg = j.get('error', {}).get('message', 'Sin respuesta de Gemini')
            return jsonify({'error': f'Gemini: {error_msg}', 'detail': j}), 500

        # ── Groq ────────────────────────────────────────────
        elif modelo == 'groq':
            r = req.post('https://api.groq.com/openai/v1/chat/completions',
                headers={'Content-Type':'application/json','Authorization':f'Bearer {GROQ_KEY}'},
                json={'model':'llama-3.3-70b-versatile','max_tokens':800,
                      'messages':[{'role':'system','content':sys_prompt},{'role':'user','content':user_msg}]},
                timeout=30)
            j = r.json()
            if 'choices' in j and j['choices']:
                return jsonify({'html': j['choices'][0]['message']['content']})
            return jsonify({'error': 'Sin respuesta de Groq', 'detail': j}), 500

        return jsonify({'error': f'Modelo desconocido: {modelo}'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── MÓDULO DULCE DETALLE — esteticas.enmerida.mx/dulce-detalle ─────────────────────
DD_MAIL = os.environ.get('DD_MAIL', os.environ.get('DEMO_MAIL', 'isai.josue@gmail.com'))
DULCE_CATALOGO = """
CATÁLOGO DULCE DETALLE MÉRIDA 2026
(Costo de envío NO incluido en ningún producto)
=== DESAYUNOS ===
Presentación Básica — $280: Croissant de jamón de pavo y queso manchego, jugo del Valle, galleta, pretzel, etiqueta de ocasión.
Chapata Básico — $280: Chapata de jamón con queso manchego, orejitas de hojaldre, chiles en raja, jugo.
Fit Básico — $300: Fruta picada o croissant jamón/queso, jugo, yogurt, galletas, pretzel, granola.
Box Sabritas — $320: Papas Sabritas, jugo, croissant jamón/queso, galletas, pretzels, chiles jalapeños. Caja cartón con etiqueta vinil.
Charola Fit Básico — $340: Fruta picada, yogurt Oikos, granola, bebida energizante sin azúcar, agua, café Starbucks, pretzels.
Box Ligero Mini / Desayuno Ligero Mini — $380: Croissant jamón/queso, fruta picada, jugo, pretzels, galletas, agua.
Box Sabritas Krispy Kreme — $420: Croissant jamón/queso, dona Krispy Kreme, Sabritas, jugo, KitKat, galleta.
Ligero Mini con Pastel — $460: Croissant jamón/queso, fruta picada, café frío, pastel mini, pretzels, galletas.
Charola Sabritas Feliz Cumpleaños — $460: Croissant jamón/queso, Sabritas, pastel individual, jugo, galletas, pretzels.
Batman Mini con Pastel — $480: Diseño Batman, vaso de colección, croissant jamón/queso, jugo, Sabritas, galletas, pretzels, pastel mini.
Snoopy Mini con Pastel — $480: Diseño Snoopy, vaso de colección, croissant jamón/queso, jugo, Sabritas, galletas, pretzels, pastel mini.
Astromelia Mini con Girasol — $520: Croissant jamón/queso, café frío, muffin, galletas, pretzels — con arreglo floral de astromelia y girasol.
Chapata Special — $520: Chapata jamón/queso, orejitas de hojaldre, Ferreros (8 pzas), pretzels en frasco, café Starbucks, jugo, cubiertos.
Astromelia — $580: Chapata jamón/queso, yogurt con fruta, orejitas, pretzels, jugo, cubiertos, taza con arreglo de astromelias.
Chapata Black — $580: Chapata jamón/queso, pretzels en frasco, orejitas, Ferreros (8 pzas), café Starbucks, jugo, café frío, cubiertos.
Romántico Black — $680: Chapata jamón/queso, ensalada frutas con yogurt/granola, pretzels, orejitas, jugo, café frío, cubiertos, base cerámica con 5 rosas rojas, charola de madera con etiqueta vinil.
Isabella — $720: Chapata jamón/queso, arreglo floral rosas rojas + follaje, pretzels en frasco, orejitas, Ferreros (8 pzas), café Starbucks, jugo, café frío, cubiertos.
Ligero Mini Premium — $880: Charola doble piso, arreglo floral 7 rosas o 2 girasoles, jugo, café frío, fruta picada, croissant jamón/queso, galletas, pretzels, KitKat. Etiqueta doble vinil.
=== BOX Y REGALOS ===
Box Snoopy — $380: Croissant jamón/queso, vaso de colección Snoopy, jugo, galletas, pretzels.
Box Corazón Compartido — $520: Croissant dulce fresa/Nutella + croissant salado jamón/queso, fresas, uvas, mini Nutella, galletas, pretzels, orejitas, pistaches, almendras, Ferreros.
Box Starbucks — $520: Croissant jamón/queso Starbucks, bebida gasificada, Ferreros (8 pzas), KitKat, Waffle Starbucks.
Box Starbucks y Rosas — $780: Arreglo floral rosas + astromelias, Agua Perrier, Waffle Starbucks, croissant jamón/queso, vaso reutilizable.
=== CANASTAS ===
Canasta Desayuno Ligero Mini — $580: Canasta mimbre, arreglo floral, fruta picada (manzana, fresa, uva, papaya), jugo, croissant jamón/queso, galletas, pretzels.
Canasta Starbucks Mini — $680: Croissant jamón/queso, café americano, dona Krispy Kreme, bebida gasificada, vaso de colección, arreglo floral girasol o 3 rosas.
Canasta Starbucks Grande — $920: Croissant jamón/queso, fruta con yogurt, Ferreros (8 pzas), bebida gasificada, vaso Starbucks, Waffle Starbucks, arreglo floral girasol o 3 rosas.
=== CHAROLAS (DESAYUNO) ===
Charola Love Chocolates — $580: Ferreros, 2 Kinder Delice, vaso Snoopy, Pulparindo, KitKat, Crunch, Paleta Payaso — con arreglo floral de rosas.
Charola Starbucks Mini — $520: Croissant jamón/queso, café americano Starbucks, vaso de colección, bebida gasificada, dona Krispy Kreme, galletas, pretzels.
Charola 6 Donas Krispy Kreme — $620: 6 donas glaseadas Krispy Kreme, bebida saborizada, café americano, galletas, pretzels, croissant jamón/queso, Ferreros (8 pzas).
Charola Love Desayuno — $680: Arreglo floral 3 rosas + follaje, croissant jamón/queso, Cocacola lata, vaso Snoopy, galletas, pretzels.
Charola de Frutas Premium — $1,100: Al menos 8 frutas de temporada en charola doble piso edición limitada, arreglo floral 7 rosas o 2 girasoles, etiquetas vinil.
=== FLORES Y ARREGLOS FLORALES ===
Flor en Base de Cartón — $160
Girasol con Astromelias y Tulia — $280
Paquete Liss Girasol — $480
Cinco Rosas y Tulia — $520
Globo con Rosas y Mariposas — $580
Corazón Doble Girasol y Astromelias — $580
Rosas y Café Starbucks — $580
Corazón de Ferreros y Rosas — $680
Letra con Rosas y Chocolates — $720
Corazón Rosas, Fresas y Chocolates — $720
Corazón con Rosas y KitKat — $780
Ramo de 24 Rosas Rosadas — $780
Ramo Buchón 100 Rosas Rojas — $3,200
=== QUESOS Y CARNES FRÍAS ===
Quesos y Carnes Frías Mini — $380
Charola Carnes Frías y Quesos — $520
Corazón de Madera con Carnes Frías — $620
Tabla Corazón con Vino — $720
Charola Carnes Frías y Cerveza — $820
Charola de Carnes y Quesos — $920
Carnes Frías Premium — $1,200
Carnes Frías Premium y Rosas — $1,300
=== CHELAS, BOTELLAS Y BEBIDAS ===
Cervezas y Botanas Mini — $420
Charola Chelas y Botanas en Frascos — $620
Box Cervezas Artesanales y Botanas — $680
Charola Cervezas Artesanales — $880
Tequila Don Julio y Botanas — $1,400
Buchanans con Botanas — $1,800
Tapete Rosas, Chocolates y Buchanan's — $2,600
"""

DULCE_PROMPT_BASE = (
    'Eres una asesora de regalos de Dulce Detalle Mérida — un negocio de desayunos sorpresa, flores, charcutería y arreglos frutales. '
    'Tu forma de comunicarte es cálida, cercana y genuina, como una amiga que te ayuda a elegir el regalo perfecto. '
    'Hablas de "tú". Usas el nombre de la persona. '
    '\n\nTONO — LA REGLA MÁS IMPORTANTE: '
    'Responde EXACTAMENTE al nivel emocional que el cliente expresó en su contexto. '
    'Si escribió poco o fue neutral → respuesta práctica, enfocada en el producto. '
    'Si fue emotivo y detallado → acompañar ese tono con calidez genuina. '
    'NUNCA asumas sentimientos que el cliente no expresó. '
    '\n\nRECUERDA SIEMPRE: el cliente está eligiendo un regalo para OTRA PERSONA. '
    '\n\nEVITA ABSOLUTAMENTE: '
    '"no dudes en contactarnos", "estamos a tu disposición", exclamaciones excesivas, lenguaje corporativo. '
    '\n\nESTRUCTURA: '
    '1. Abre con el nombre y una frase que demuestre que leíste su caso específico. '
    '2. Lista los productos recomendados — nombre en negrita + por qué encaja. '
    '3. Cierra con una invitación simple a coordinar la entrega. '
    '\n\nFORMATO HTML — solo estas etiquetas: <p>, <strong>, <ul>, <li>. '
    'NO uses markdown, NO asteriscos. NO menciones precios. '
    f'\n\nCATÁLOGO DISPONIBLE:\n{DULCE_CATALOGO}'
)

@app.route('/dulce-detalle')
def dulce_detalle():
    with open(os.path.join(os.path.dirname(__file__), 'formulario-dulce-detalle.html'), encoding='utf-8') as f:
        return f.read()

@app.route('/dulce-detalle/recomendar', methods=['POST'])
def dulce_recomendar():
    """Proxy multi-modelo para el formulario Dulce Detalle — CORREGIDO."""
    try:
        data   = request.get_json(force=True)
        perfil = data.get('perfil', '')
        modelo = data.get('modelo', 'claude')
        if not perfil:
            return jsonify({'error': 'Sin datos de perfil'}), 400

        user_msg = f'Por favor genera una recomendación personalizada para este cliente:\n\n{perfil}'

        # ── Claude ──────────────────────────────────────────
        if modelo == 'claude':
            resp = req.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': CLAUDE_KEY,
                    'anthropic-version': '2023-06-01',
                    'content-type': 'application/json'
                },
                json={
                    'model': 'claude-haiku-4-5-20251001',
                    'max_tokens': 900,
                    'system': DULCE_PROMPT_BASE,
                    'messages': [{'role': 'user', 'content': user_msg}]
                },
                timeout=30
            )
            print(f'[dulce/claude] status={resp.status_code}')
            if resp.status_code != 200:
                print(f'[dulce/claude] ERROR: {resp.text[:300]}')
                return jsonify({'error': f'Claude: {resp.status_code}'}), 500
            texto = resp.json()['content'][0]['text']

        # ── Gemini ──────────────────────────────────────────
        elif modelo == 'gemini':
            # ✅ Modelo corregido para coincidir con demo_recomendar()
            url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_KEY}'
            resp = req.post(
                url,
                json={
                    'contents': [{'parts': [{'text': DULCE_PROMPT_BASE + '\n\n' + user_msg}]}],
                    'generationConfig': {'maxOutputTokens': 900, 'temperature': 0.7}
                },
                timeout=30
            )
            print(f'[dulce/gemini] status={resp.status_code}')
            if resp.status_code != 200:
                print(f'[dulce/gemini] ERROR: {resp.text[:300]}')
                return jsonify({'error': f'Gemini: {resp.status_code}'}), 500
            rj = resp.json()
            if 'candidates' not in rj or not rj['candidates']:
                print(f'[dulce/gemini] Sin candidatos: {rj}')
                return jsonify({'error': 'Gemini: sin respuesta'}), 500
            texto = rj['candidates'][0]['content']['parts'][0]['text']

        # ── Groq ────────────────────────────────────────────
        elif modelo == 'groq':
            resp = req.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'},
                json={
                    # ✅ Modelo corregido para coincidir con demo_recomendar()
                    'model': 'llama-3.3-70b-versatile',
                    'max_tokens': 900,
                    'messages': [
                        {'role': 'system', 'content': DULCE_PROMPT_BASE},
                        {'role': 'user', 'content': user_msg}
                    ]
                },
                timeout=30
            )
            print(f'[dulce/groq] status={resp.status_code}')
            if resp.status_code != 200:
                print(f'[dulce/groq] ERROR: {resp.text[:300]}')
                return jsonify({'error': f'Groq: {resp.status_code}'}), 500
            rj = resp.json()
            if 'choices' not in rj or not rj['choices']:
                print(f'[dulce/groq] Sin choices: {rj}')
                return jsonify({'error': 'Groq: sin respuesta'}), 500
            texto = rj['choices'][0]['message']['content']

        else:
            return jsonify({'error': f'Modelo desconocido: {modelo}'}), 400

        texto = htmllib.unescape(texto)
        texto = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', texto)
        texto = re.sub(r'\*(.+?)\*', r'<em>\1</em>', texto)

        return jsonify({'html': texto})

    except Exception as e:
        print(f'[dulce/recomendar] EXCEPCION: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/dulce-detalle/cita', methods=['POST'])
def dulce_cita():
    """Recibe solicitud de pedido y envía correo de notificación."""
    try:
        import resend as resend_lib
        resend_lib.api_key = RESEND_KEY

        d = request.get_json(force=True)
        nombre      = d.get('nombre', '')
        whatsapp    = d.get('whatsapp', '')
        email       = d.get('email', '')
        fecha       = d.get('fecha_entrega', 'No especificada')
        direccion   = d.get('direccion', 'No especificada')
        notas       = d.get('notas', '')
        para        = d.get('para', '')
        motivo      = d.get('motivo', '')
        tipo_regalo = d.get('tipo_regalo', '')
        presupuesto = d.get('presupuesto', '')

        cuerpo_negocio = f"""
🎁 Nueva solicitud de pedido · Dulce Detalle · esteticas.enmerida.mx/dulce-detalle
| 👤 Nombre | {nombre} |
| --- | --- |
| 📱 WhatsApp | {whatsapp} |
| ✉️ Correo | {email} |
| 🎁 Para quién | {para} |
| 🎉 Motivo | {motivo} |
| 🛍️ Tipo regalo | {tipo_regalo} |
| 💛 Presupuesto | {presupuesto} |
| 📅 Entrega | {fecha} |
| 📍 Dirección | {direccion} |
| 📝 Notas | {notas or '—'} |
"""
        cuerpo_cliente = f"""
🌸 ¡Hola, {nombre}!
Recibimos tu solicitud en Dulce Detalle Mérida
Gracias por confiar en nosotros para este regalo especial.
Nos pondremos en contacto contigo pronto al {whatsapp} para coordinar todos los detalles.
| 🎁 Para quién | {para} |
| --- | --- |
| 🎉 Motivo | {motivo} |
| 📅 Entrega | {fecha} |
Dulce Detalle · Corporativo de Regalos · Mérida, Yucatán
"""
        resend_lib.Emails.send({
            'from': MAIL_FROM,
            'to': [DD_MAIL],
            'subject': f'🎁 Nuevo pedido — {nombre} ({motivo})',
            'html': cuerpo_negocio
        })

        if email:
            resend_lib.Emails.send({
                'from': MAIL_FROM,
                'to': [email],
                'subject': '🌸 Recibimos tu solicitud — Dulce Detalle Mérida',
                'html': cuerpo_cliente
            })

        return jsonify({'ok': True})

    except Exception as e:
        print(f'[dulce/cita] error: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)