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

    date = fields.Date(
        string='Date du paiement',
        default=fields.Date.context_today,
        required=True,
    )

    reception_date = fields.Date(
        string='Date de réception',
        default=fields.Date.context_today,
    )

    @api.onchange('reception_date')
    def _onchange_reception_date(self):
        if self.reception_date:
            for line in self.cheque_line_ids:
                line.reception_date = self.reception_date
            for line in self.effet_line_ids:
                line.reception_date = self.reception_date

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
    def action_parse_pdf_via_ai(self):
        self.ensure_one()
        if not self.scan_document:
            from odoo.exceptions import UserError
            raise UserError("Veuillez d'abord uploader un document scanné.")

        api_key = self.env['ir.config_parameter'].sudo().get_param('tresorerie_chq.gemini_key')
        if not api_key:
            from odoo.exceptions import UserError
            raise UserError("La clé API Google Gemini n'est pas configurée (tresorerie_chq.gemini_key).")

        import requests
        import json

        pdf_b64 = self.scan_document.decode('utf-8') if isinstance(self.scan_document, bytes) else self.scan_document

        banks = self.env['tresorerie_chq.bank'].sudo().search([])
        bank_names = ", ".join(banks.mapped('name'))

        doc_type = "chèques" if self.payment_type == 'cheque' else "effets"

        prompt_text = f"""Vous êtes un assistant financier. Vous recevez un scan PDF contenant un ou plusieurs {doc_type}.
Votre but est d'extraire les informations pour chaque {doc_type[:-1]} trouvé dans le document.
Il est ABSOLUMENT CRUCIAL que vous retourniez les éléments dans l'ordre exact où ils apparaissent dans le document PDF (de haut en bas, page par page).

Retournez UNIQUEMENT un objet JSON valide, sans markdown, contenant une liste nommée "items".
Pour chaque élément, extrayez :
1. "numero": Le numéro du {doc_type[:-1]} (généralement 7 chiffres ou moin pour un chèque).
2. "montant": Le montant du {doc_type[:-1]} (uniquement des chiffres, ex: 1500.50). ATTENTION : Lisez attentivement le montant écrit en lettres (qui se trouve souvent au milieu du document, en arabe ou en français) et croisez-le avec le montant en chiffres (en haut à droite) pour garantir l'exactitude absolue du montant extrait.
3. "date_echeance": La date d'échéance écrite sur le document, au format YYYY-MM-DD.
4. "banque": Le nom de la banque (à lire souvent dans le logo en HAUT à GAUCHE ou au CENTRE du chèque). Essayez de faire correspondre avec l'une de ces banques : {bank_names}.
5. "porteur": Le nom du titulaire du compte / porteur. C'est le nom imprimé situé en BAS au CENTRE, généralement juste en dessous du "Compte n°". NE CHOISISSEZ PAS le nom de l'agence (qui se trouve à gauche sous "Payable à"). ATTENTION : Retirez ABSOLUMENT toutes les civilités et titres du texte extrait (comme MR, M., MONSIEUR, MME, MADAME, MLLE) pour ne garder strictement que le nom et le prénom.

Exemple de réponse attendue:
{{
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

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt_text
                        },
                        {
                            "inlineData": {
                                "mimeType": "application/pdf",
                                "data": pdf_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            if resp.status_code != 200:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                from odoo.exceptions import UserError
                raise UserError(f"Erreur de l'API Gemini : {err_msg}")
            
            ai_data = resp.json()
        except Exception as e:
            from odoo.exceptions import UserError
            raise UserError(f"Erreur de communication avec l'IA : {str(e)}")

        try:
            raw_content = ai_data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            from odoo.exceptions import UserError
            raise UserError("L'IA n'a retourné aucune donnée lisible.")

        try:
            result = json.loads(raw_content)
        except Exception:
            from odoo.exceptions import UserError
            raise UserError(f"L'IA a retourné un format JSON invalide : {raw_content}")

        items = result.get('items', [])
        if not items:
            from odoo.exceptions import UserError
            raise UserError("Aucun chèque/effet n'a pu être identifié dans ce document.")

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
                vals['check_date'] = item.get('date_echeance')
            
            lines_to_create.append((0, 0, vals))
            current_sequence += 10

        if lines_to_create:
            if self.payment_type == 'cheque':
                self.write({'cheque_line_ids': lines_to_create})
            else:
                self.write({'effet_line_ids': lines_to_create})

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

