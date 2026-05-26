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
        ('cheque', 'ChÃ¨ques'),
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

        api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
        if not api_key:
            from odoo.exceptions import UserError
            raise UserError("La clé API OpenAI n'est pas configurée (whatsapp_stock.openai_key).")

        import requests
        import json

        pdf_b64 = self.scan_document.decode('utf-8') if isinstance(self.scan_document, bytes) else self.scan_document

        banks = self.env['tresorerie_chq.bank'].sudo().search([])
        bank_names = ", ".join(banks.mapped('name'))

        doc_type = "chèques" if self.payment_type == 'cheque' else "effets"

        prompt_text = f\"\"\"Vous êtes un assistant financier. Vous recevez un scan PDF contenant un ou plusieurs {doc_type}.
Votre but est d'extraire les informations pour chaque {doc_type[:-1]} trouvé dans le document.

Retournez UNIQUEMENT un objet JSON valide, sans markdown, contenant une liste nommée "items".
Pour chaque élément, extrayez :
1. "numero": Le numéro du {doc_type[:-1]} (généralement 7 chiffres pour un chèque).
2. "montant": Le montant du {doc_type[:-1]} (uniquement des chiffres, ex: 1500.50).
3. "date_echeance": La date d'échéance écrite sur le document, au format YYYY-MM-DD.
4. "banque": Le nom de la banque visible sur le document. Essayez de faire correspondre avec l'une de ces banques : {bank_names}.

Exemple de réponse attendue:
{{
  "items": [
    {{
      "numero": "2102888",
      "montant": 18746.43,
      "date_echeance": "2026-05-16",
      "banque": "Attijariwafa Bank"
    }}
  ]
}}\"\"\"

        payload = {
            "model": "gpt-4o",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": "scan.pdf",
                            "file_data": f"data:application/pdf;base64,{pdf_b64}"
                        },
                        {
                            "type": "input_text",
                            "text": prompt_text
                        }
                    ]
                }
            ],
            "text": {
                "format": {
                    "type": "json_object"
                }
            },
            "temperature": 0.0,
            "max_output_tokens": 1500
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=120)
            if resp.status_code != 200:
                err_msg = resp.json().get("error", {}).get("message", resp.text)
                from odoo.exceptions import UserError
                raise UserError(f"Erreur de l'API OpenAI : {err_msg}")
            
            ai_data = resp.json()
        except Exception as e:
            from odoo.exceptions import UserError
            raise UserError(f"Erreur de communication avec l'IA : {str(e)}")

        raw_content = ""
        for output_item in ai_data.get("output", []):
            for content_item in output_item.get("content", []):
                if content_item.get("type") == "output_text":
                    raw_content = content_item.get("text", "")
                    break

        if not raw_content:
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
        for item in items:
            bank_id = False
            bank_name = item.get('banque', '')
            if bank_name:
                bank_record = self.env['tresorerie_chq.bank'].search([('name', '=ilike', bank_name)], limit=1)
                if not bank_record:
                    bank_record = self.env['tresorerie_chq.bank'].search([('name', 'ilike', bank_name)], limit=1)
                if bank_record:
                    bank_id = bank_record.id

            vals = {
                'note': item.get('numero', ''),
                'amount': float(item.get('montant') or 0.0),
                'bank_id': bank_id,
            }
            if item.get('date_echeance'):
                vals['check_date'] = item.get('date_echeance')
            
            lines_to_create.append((0, 0, vals))

        if lines_to_create:
            if self.payment_type == 'cheque':
                self.write({'cheque_line_ids': lines_to_create})
            else:
                self.write({'effet_line_ids': lines_to_create})
