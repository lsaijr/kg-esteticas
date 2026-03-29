@app.route('/dulce-detalle/recomendar', methods=['POST'])
def dulce_recomendar():
    """Proxy multi-modelo para el formulario Dulce Detalle — CON PROMPTS MEJORADOS."""
    try:
        data   = request.get_json(force=True)
        perfil = data.get('perfil', '')
        modelo = data.get('modelo', 'claude')
        if not perfil:
            return jsonify({'error': 'Sin datos de perfil'}), 400

        user_msg = f'Por favor genera una recomendación personalizada para este cliente:\n\n{perfil}'

        # ── Prompt base común ─────────────────────────────────
        prompt_base = DULCE_PROMPT_BASE

        # ── Prompts específicos por modelo ───────────────────
        if modelo == 'groq':
            # ✅ Groq necesita instrucciones más explícitas para detalle y tacto
            system_prompt = prompt_base + (
                '\n\n🎯 INSTRUCCIONES ADICIONALES PARA CALIDAD:\n'
                '• Escribe mínimo 300 palabras — cada recomendación debe tener 2-3 oraciones completas\n'
                '• Usa un tono CÁLIDO y EMPÁTICO — como una amiga que conoce bien los gustos del cliente\n'
                '• Menciona detalles específicos del perfil (nombre, motivo, relación, presupuesto) en CADA párrafo\n'
                '• Explica POR QUÉ cada producto encaja con esta persona en particular\n'
                '• Evita frases genéricas como "espero que le guste" — sé específica sobre el impacto emocional\n'
                '• Cierra con una invitación natural, sin presión comercial\n'
                '• Máximo 450 palabras'
            )
        elif modelo == 'gemini':
            # ✅ Gemini tiende a ser muy breve — reforzar detalle
            system_prompt = prompt_base + (
                '\n\n🎯 INSTRUCCIONES ADICIONALES PARA CALIDAD:\n'
                '• Desarrolla cada recomendación con 2-3 oraciones — no listes productos sin contexto\n'
                '• Conecta emocionalmente con el motivo del regalo (cumpleaños, aniversario, agradecimiento, etc.)\n'
                '• Menciona el nombre del cliente y su relación con quien recibe el regalo\n'
                '• Explica qué hace especial cada producto PARA ESTA OCASIÓN ESPECÍFICA\n'
                '• Tono: cercano pero profesional — cálida como una asesora de confianza\n'
                '• Máximo 400 palabras'
            )
        else:
            # Claude — funciona bien con el prompt base
            system_prompt = prompt_base + '\n\n• Máximo 350 palabras • Sé cálida y específica'

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
                    'system': system_prompt,
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
                    'system_instruction': {'parts': [{'text': system_prompt}]},
                    'contents': [{'parts': [{'text': user_msg}]}],
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
                        {'role': 'system', 'content': system_prompt},
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
