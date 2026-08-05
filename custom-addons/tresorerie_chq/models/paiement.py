from odoo import models, fields, api


class TresoreriePaiement(models.Model):
    _name = 'tresorerie_chq.paiement'
    _description = 'Paiement (TrÃ©sorerie ChÃ¨ques & Effets)'
    _order = 'create_date desc'

    client_id = fields.Many2one(
        'tresorerie_chq.client',
        string='Client',
        required=True,
        ondelete='restrict',
    )

    payment_type = fields.Selection([
        ('cheque', 'Chèques'),
        ('effet', 'Effets'),
    ], string='Type de paiement', required=True, default='cheque')

    is_soufiane = fields.Boolean(
        compute='_compute_is_soufiane',
        string='Est Soufiane',
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validé')
    ], string='Statut', default='draft', required=True, tracking=True)

    date = fields.Date(
        string='Date du paiement',
        default=fields.Date.context_today,
        required=True,
    )

    reception_date = fields.Date(
        string='Date de réception',
        default=fields.Date.context_today,
    )

    # The reception_date on cheques and effets is now a related field.

    # ------------------------------------------------------------------
    # ChÃ¨ques et Effets: separate detail lines
    # ------------------------------------------------------------------
    cheque_line_ids = fields.One2many(
        'tresorerie_chq.cheque',
        'paiement_id',
        string='ChÃ¨ques',
    )

    effet_line_ids = fields.One2many(
        'tresorerie_chq.effet',
        'paiement_id',
        string='Effets',
    )

    # Computed total amount depending on payment type
    amount = fields.Float(
        string='Montant total',
        compute='_compute_amount',
        store=True,
        digits=(10, 2),
    )

    # Computed single check date for backward/sorting compatibility
    check_date = fields.Date(
        string='Date d\'Ã©chÃ©ance',
        compute='_compute_check_date',
        store=True,
    )

    scan_document = fields.Binary(
        string="Scan Document",
        attachment=True,
        help="Fichier de scan global pour le paiement"
    )
    scan_document_name = fields.Char(string="Nom du fichier scan")

    # ------------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------------
    @api.depends('client_id.name')
    def _compute_is_soufiane(self):
        for rec in self:
            rec.is_soufiane = rec.client_id and rec.client_id.name == 'Soufiane'

    @api.depends('payment_type', 'cheque_line_ids.amount', 'effet_line_ids.amount')
    def _compute_amount(self):
        for rec in self:
            if rec.payment_type == 'cheque':
                rec.amount = sum(rec.cheque_line_ids.mapped('amount'))
            elif rec.payment_type == 'effet':
                rec.amount = sum(rec.effet_line_ids.mapped('amount'))
            else:
                rec.amount = 0.0

    @api.depends('payment_type', 'cheque_line_ids.check_date', 'effet_line_ids.check_date')
    def _compute_check_date(self):
        for rec in self:
            dates = []
            if rec.payment_type == 'cheque' and rec.cheque_line_ids:
                dates = [l.check_date for l in rec.cheque_line_ids if l.check_date]
            elif rec.payment_type == 'effet' and rec.effet_line_ids:
                dates = [l.check_date for l in rec.effet_line_ids if l.check_date]
            rec.check_date = min(dates) if dates else False
    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_validate(self):
        for rec in self:
            rec.state = 'validated'

    def action_draft(self):
        # Allow admin (e.g., Tresorerie Manager) to revert to draft
        if not self.env.user.has_group('tresorerie_chq.group_tresorerie_chq_manager'):
            from odoo.exceptions import AccessError
            raise AccessError("Seul un responsable peut remettre le paiement en brouillon.")
        for rec in self:
            rec.state = 'draft'

    def action_parse_pdf_via_ai(self):
        self.ensure_one()
        if not self.scan_document:
            from odoo.exceptions import UserError
            raise UserError("Aucun document scanné n'est rattaché à cette entrée.")

        api_key = self.env['ir.config_parameter'].sudo().get_param('tresorerie_chq.gemini_key', '').strip()
        claude_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.claude_key', '').strip()
        
        if not api_key:
            from odoo.exceptions import UserError
            raise UserError("La clé API Gemini n'est pas configurée dans les paramètres systèmes (tresorerie_chq.gemini_key).")
            
        banks = self.env['tresorerie_chq.bank'].search([])
        bank_names = ", ".join(banks.mapped('name'))

        doc_type = "chèques" if self.payment_type == 'cheque' else "effets"

        prompt_text = f"""Vous êtes un assistant financier. Vous recevez un scan PDF contenant un ou plusieurs {doc_type}.
Votre but est d'extraire les informations pour chaque {doc_type[:-1]} trouvé dans le document.
Il est ABSOLUMENT CRUCIAL que vous retourniez les éléments dans l'ordre exact où ils apparaissent dans le document PDF (de haut en bas, page par page).

⚠️ RÈGLE DE VIE OU DE MORT : Vous DEVEZ extraire ABSOLUMENT TOUS LES CHÈQUES présents dans le document. Même s'il y a 20, 30 ou 50 chèques répartis sur plusieurs pages, vous ne devez SOUS AUCUN PRÉTEXTE vous arrêter en cours de route. Un chèque oublié est une faute grave. Traitez chaque page de la première à la dernière ligne.

Retournez UNIQUEMENT un objet JSON valide, sans markdown, structuré de cette façon :
1. "total_attendu": (Entier) Le nombre TOTAL exact de chèques/effets que vous avez trouvés et que vous allez extraire. Comptez-les bien tous.
2. "items": La liste de ces chèques.
Pour chaque élément de la liste, extrayez :
1. "numero": Le numéro du {doc_type[:-1]} (généralement 7 chiffres ou moin pour un chèque).
2. "montant": Le montant du {doc_type[:-1]} (uniquement des chiffres, ex: 1500.50). ATTENTION : Lisez attentivement le montant écrit en lettres (qui se trouve souvent au milieu du document, en arabe ou en français) et croisez-le avec le montant en chiffres (en haut à droite) pour garantir l'exactitude absolue du montant extrait.
3. "date_echeance": La date d'échéance écrite sur le document, au format YYYY-MM-DD.
4. "banque": Le nom de la banque (à lire souvent dans le logo en HAUT à GAUCHE ou au CENTRE du chèque). Essayez de faire correspondre avec l'une de ces banques : {bank_names}.
5. "porteur": Le nom du titulaire du compte / porteur. C'est le nom imprimé situé en BAS au CENTRE, généralement juste en dessous du "Compte n°". NE CHOISISSEZ PAS le nom de l'agence (qui se trouve à gauche sous "Payable à"). ATTENTION : Retirez ABSOLUMENT toutes les civilités et titres du texte extrait (comme MR, M., MONSIEUR, MME, MADAME, MLLE) pour ne garder strictement que le nom et le prénom.

Exemple de réponse attendue:
{{
  "total_attendu": 1,
  "items": [
    {{
      "numero": "2102888",
      "montant": 18746.43,
      "date_echeance": "2026-05-16",
      "banque": "Attijariwafa Bank",
      "porteur": "Ali Yassine"
    }}
  ]
}}"""

        import base64
        pdf_bytes = base64.b64decode(self.scan_document)
        
        # Lancer Gemini et OpenAI en parallèle
        from concurrent.futures import ThreadPoolExecutor
        import json
        import requests
        import re

        def call_gemini():
            upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
            upload_headers = {
                "X-Goog-Upload-Protocol": "raw",
                "X-Goog-Upload-Header-Content-Type": "application/pdf",
                "Content-Type": "application/pdf"
            }
            try:
                upload_resp = requests.post(upload_url, headers=upload_headers, data=pdf_bytes, timeout=120)
                if upload_resp.status_code != 200:
                    return {"error": f"Erreur Gemini Upload: {upload_resp.text}"}
                
                file_uri = upload_resp.json().get("file", {}).get("uri")
                if not file_uri:
                    return {"error": "Impossible de récupérer l'URI Gemini."}
                    
                payload = {
                    "contents": [{"parts": [{"text": prompt_text}, {"fileData": {"mimeType": "application/pdf", "fileUri": file_uri}}]}],
                    "generationConfig": {"temperature": 0.0, "maxOutputTokens": 8192}
                }
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-latest:generateContent?key={api_key}"
                resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=120)
                
                if resp.status_code != 200:
                    return {"error": f"Erreur API Gemini: {resp.text}"}
                    
                raw_content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                clean_content = re.sub(r'^```(json)?', '', raw_content.strip(), flags=re.IGNORECASE)
                clean_content = re.sub(r'```$', '', clean_content.strip()).strip()
                
                try:
                    return json.loads(clean_content)
                except Exception as e:
                    last_brace_idx = clean_content.rfind('}')
                    if last_brace_idx != -1:
                        return json.loads(clean_content[:last_brace_idx+1] + ']}')
                    return {"error": f"JSON Gemini Invalide: {str(e)}"}
            except Exception as e:
                return {"error": f"Exception Gemini: {str(e)}"}

        def call_claude():
            if not claude_key:
                return {"error": "Clé Claude manquante."}
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                base64_images = []
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    # Augmentation de la résolution de l'image (Zoom x4) pour éviter les hallucinations
                    pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
                    img_bytes = pix.tobytes("png")
                    base64_images.append(base64.b64encode(img_bytes).decode('utf-8'))
                    
                content_array = [{"type": "text", "text": prompt_text}]
                for img in base64_images:
                    content_array.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img
                        }
                    })
                    
                messages = [
                    {
                        "role": "user",
                        "content": content_array
                    }
                ]
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": claude_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": "claude-sonnet-5",
                    "max_tokens": 8192,
                    "messages": messages
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=120)
                if resp.status_code != 200:
                    return {"error": f"Erreur API Claude: {resp.text}"}
                    
                resp_json = resp.json()
                try:
                    raw_content = ""
                    for item in resp_json.get("content", []):
                        if item.get("type") == "text":
                            raw_content = item.get("text", "")
                            break
                    if not raw_content:
                        raise KeyError("Aucun bloc de texte trouvé")
                except (KeyError, IndexError):
                    return {"error": f"Format de réponse Claude inattendu: {json.dumps(resp_json)}"}
                
                raw_content = raw_content.strip()
                json_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw_content, re.DOTALL)
                if json_match:
                    clean_content = json_match.group(1).strip()
                else:
                    start_idx = raw_content.find('{')
                    start_arr_idx = raw_content.find('[')
                    valid_starts = [i for i in (start_idx, start_arr_idx) if i != -1]
                    if valid_starts:
                        start = min(valid_starts)
                        end_char = '}' if start == start_idx else ']'
                        end = raw_content.rfind(end_char)
                        clean_content = raw_content[start:end+1] if (end != -1 and end > start) else raw_content
                    else:
                        clean_content = raw_content
                
                return json.loads(clean_content)
            except Exception as e:
                return {"error": f"Exception Claude: {str(e)}"}

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_gemini = executor.submit(call_gemini)
            future_claude = executor.submit(call_claude)
            result_gemini = future_gemini.result()
            result_claude = future_claude.result()

        from odoo.exceptions import UserError
        if "error" in result_gemini:
            raise UserError(f"Echec Gemini: {result_gemini['error']}")
            
        def similar(a, b):
            from difflib import SequenceMatcher
            if not a and not b: return True
            if not a or not b: return False
            return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio() > 0.8

        is_consensus = True
        consensus_errors = []
        if "error" in result_claude:
            is_consensus = False
            consensus_errors.append(f"Erreur Claude: {result_claude['error']}")
        else:
            g_items = result_gemini.get('items', [])
            o_items = result_claude.get('items', [])
            if len(g_items) != len(o_items):
                is_consensus = False
                consensus_errors.append(f"Nombre différent : Gemini a trouvé {len(g_items)}, Claude a trouvé {len(o_items)}.")
            else:
                for i in range(len(g_items)):
                    g = g_items[i]
                    o = o_items[i]
                    # Chiffres : Correspondance exacte
                    if str(g.get('numero') or '').strip() != str(o.get('numero') or '').strip():
                        is_consensus = False
                        consensus_errors.append(f"Ligne {i+1}: Numéro différent ({g.get('numero')} vs {o.get('numero')})")
                    if float(g.get('montant') or 0) != float(o.get('montant') or 0):
                        is_consensus = False
                        consensus_errors.append(f"Ligne {i+1}: Montant différent ({g.get('montant')} vs {o.get('montant')})")
                    if str(g.get('date_echeance') or '').strip() != str(o.get('date_echeance') or '').strip():
                        is_consensus = False
                        consensus_errors.append(f"Ligne {i+1}: Date différente ({g.get('date_echeance')} vs {o.get('date_echeance')})")
                    # Texte : Tolérance
                    if not similar(g.get('banque'), o.get('banque')):
                        is_consensus = False
                        consensus_errors.append(f"Ligne {i+1}: Banque très différente ({g.get('banque')} vs {o.get('banque')})")
                    
                    def clean_porteur(p):
                        p_str = str(p or '').lower().strip()
                        p_str = re.sub(r'^(mr|m|mme|mlle)\b\.?\s*', '', p_str)
                        return p_str.replace(" ", "")
                        
                    porteur_g = clean_porteur(g.get('porteur'))
                    porteur_o = clean_porteur(o.get('porteur'))
                    if porteur_g != porteur_o:
                        is_consensus = False
                        consensus_errors.append(f"Ligne {i+1}: Porteur différent ({g.get('porteur')} vs {o.get('porteur')})")

        items = result_gemini.get('items', [])
        if not items:
            raise UserError("Aucun chèque/effet n'a pu être identifié par Gemini.")

        lines_to_create = []
        current_sequence = 10
        for item in items:
            bank_id = False
            bank_name = item.get('banque', '')
            if bank_name:
                bank_record = self.env['tresorerie_chq.bank'].search([('name', '=ilike', bank_name)], limit=1)
                if not bank_record:
                    bank_record = self.env['tresorerie_chq.bank'].search([('name', 'ilike', bank_name)], limit=1)
                if bank_record:
                    bank_id = bank_record.id

            owner_id = False
            owner_name = item.get('porteur', '')
            if owner_name:
                owner_record = self.env['tresorerie_chq.effets.owner'].search([('name', '=ilike', owner_name)], limit=1)
                if not owner_record:
                    owner_record = self.env['tresorerie_chq.effets.owner'].create({'name': owner_name})
                owner_id = owner_record.id

            vals = {
                'sequence': current_sequence,
                'note': item.get('numero', ''),
                'amount': float(item.get('montant') or 0.0),
                'bank_id': bank_id,
                'owner_id': owner_id,
                'ai_raw_prediction': json.dumps(item, ensure_ascii=False),
                'is_ai_extracted': True,
            }
            if self.reception_date:
                vals['reception_date'] = self.reception_date
            if item.get('date_echeance'):
                date_str = str(item.get('date_echeance')).strip()
                try:
                    from datetime import datetime
                    datetime.strptime(date_str, '%Y-%m-%d')
                    vals['check_date'] = date_str
                except ValueError:
                    pass
            
            lines_to_create.append((0, 0, vals))
            current_sequence += 10

        if lines_to_create:
            if self.payment_type == 'cheque':
                self.write({'cheque_line_ids': lines_to_create})
            else:
                self.write({'effet_line_ids': lines_to_create})
                
        if is_consensus:
            self.write({'state': 'validated'})

        return {
            'total_expected': result_gemini.get('total_attendu', 0),
            'extracted_count': len(lines_to_create),
            'is_consensus': is_consensus,
            'consensus_errors': consensus_errors
        }

    def action_confirm_ai_data(self):
        """Parcourt les lignes extraites par l'IA et crée les données d'entraînement avec les valeurs actuelles."""
        self.ensure_one()
        import json
        lines = self.cheque_line_ids if self.payment_type == 'cheque' else self.effet_line_ids
        
        ai_lines = lines.filtered(lambda l: l.is_ai_extracted and l.ai_raw_prediction)
        if not ai_lines:
            from odoo.exceptions import UserError
            raise UserError("Aucune donnée extraite par l'IA n'a été trouvée pour ce paiement.")
        
        training_obj = self.env['tresorerie_chq.ai.training']
        created_count = 0
        updated_count = 0
        
        for line in ai_lines:
            validated = {
                'numero': line.note,
                'montant': line.amount,
                'date_echeance': str(line.check_date) if line.check_date else '',
                'banque': line.bank_id.name if line.bank_id else '',
                'porteur': line.owner_id.name if line.owner_id else '',
            }
            
            existing = training_obj.search([
                ('paiement_id', '=', self.id),
                ('document_type', '=', self.payment_type),
                ('ai_prediction', '=', line.ai_raw_prediction)
            ], limit=1)
            
            if existing:
                existing.write({'validated_data': json.dumps(validated, ensure_ascii=False)})
                updated_count += 1
            else:
                training_obj.create({
                    'paiement_id': self.id,
                    'document_type': self.payment_type,
                    'ai_prediction': line.ai_raw_prediction,
                    'validated_data': json.dumps(validated, ensure_ascii=False),
                })
                created_count += 1
                
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Succès',
                'message': f'{created_count} créés, {updated_count} mis à jour dans le dataset IA.',
                'type': 'success',
                'sticky': False,
            }
        }

