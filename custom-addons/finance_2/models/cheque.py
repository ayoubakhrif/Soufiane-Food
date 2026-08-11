from odoo import models, fields, api
from datetime import timedelta

class Finance2Cheque(models.Model):
    _name = 'finance2.cheque'
    _description = 'Chèque Physique (Finance 2)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='N° Chèque', required=False, tracking=True)
    ste_id = fields.Many2one('finance2.ste', string='Société', required=False, tracking=True)
    benif_id = fields.Many2one('finance2.benif', string='Bénéficiaire', tracking=True)
    
    amount_total = fields.Float(string='Montant Total', tracking=True)
    
    type = fields.Selection([('cheque', 'Chèque'), ('effet', 'Effet')], string='Type', default='cheque', tracking=True)
    chq_certifie = fields.Boolean(string='Chq certifié', tracking=True)
    journal = fields.Char(string='Journal', tracking=True)
    personne_id = fields.Many2one('finance2.personne', string='Personnes', tracking=True)
    serie_facture = fields.Char(string='Série de facture', tracking=True)
    
    date_emission = fields.Date(string="Date d'émission", tracking=True)
    date_echeance = fields.Date(string="Date d'échéance", tracking=True)
    date_encaissement = fields.Date(string="Date d'encaissement", tracking=True)
    
    commentaire = fields.Text(string="Commentaire")
    
    # Documents
    chq_vide_pdf = fields.Binary(string='Chèque vide (PDF)', attachment=True)
    chq_vide_filename = fields.Char(string='Nom du fichier Chèque vide')
    
    doc_pdf = fields.Binary(string='Documentation (PDF)', attachment=True)
    doc_filename = fields.Char(string='Nom du fichier Documentation')
    
    # Workflow Status
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('reserve', 'Réserve'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
        ('annule', 'Annulé'),
    ], string='État', default='brouillon', tracking=True, required=True)
    
    # Suivi Logistique
    remis_a_id = fields.Many2one('finance2.personne', string='Remis à', tracking=True)
    date_remise = fields.Date(string='Date de remise (Actif)', tracking=True)
    
    # Répartitions
    repartition_ids = fields.One2many('finance2.repartition', 'cheque_id', string='Répartitions')


    @api.model_create_multi
    def create(self, vals_list):
        records = super(Finance2Cheque, self).create(vals_list)
        for rec in records:
            if rec.chq_vide_pdf and not rec.name:
                rec._extract_empty_cheque_data()
        return records

    def write(self, vals):
        res = super(Finance2Cheque, self).write(vals)
        if 'chq_vide_pdf' in vals and vals['chq_vide_pdf']:
            for rec in self:
                if not rec.name:
                    rec._extract_empty_cheque_data()
        return res

    def _extract_empty_cheque_data(self):
        for rec in self:
            if not rec.chq_vide_pdf:
                continue

            api_key = self.env['ir.config_parameter'].sudo().get_param('whatsapp_stock.openai_key')
            if not api_key:
                continue

            import requests
            import json

            pdf_b64 = rec.chq_vide_pdf.decode('utf-8') if isinstance(rec.chq_vide_pdf, bytes) else rec.chq_vide_pdf
            
            stes = self.env['finance2.ste'].sudo().search([])
            stes_names = ", ".join(stes.mapped('name'))
            
            persos = self.env['finance2.personne'].sudo().search([])
            persos_names = ", ".join(persos.mapped('name'))

            prompt_text = f"""Vous êtes un assistant financier. Vous recevez un scan d'un chèque vide.
Votre but est d'extraire les informations suivantes.
1. "chq": Le numéro du chèque (généralement 7 chiffres, ex: 2102888).
2. "ste": L'abréviation de la société émettrice. Essayez de faire correspondre exactement avec l'une de ces abréviations : {stes_names}. 
   - Soufiane Nuts = SN
   - Soufiane Foods = SF
   - Leader One = LO
   - Pacific Fruit = PF
   - Maruk = MR
3. "date_emission": La date qui se situe sur le cachet en dessous (la première date inscrite), au format YYYY-MM-DD.
4. "personne": La personne écrite sur le cachet (sur la deuxième ligne). Essayez de faire correspondre avec l'un de ces noms : {persos_names}.

Retournez UNIQUEMENT un objet JSON valide, sans markdown.
Exemple:
{{
  "chq": "2102888",
  "ste": "SN",
  "date_emission": "2026-05-18",
  "personne": "Abderzak"
}}"""

            payload = {
                "model": "gpt-4o",
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_file",
                                "filename": "cheque.pdf",
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
                "max_output_tokens": 800
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=60)
                if resp.status_code != 200:
                    continue
                ai_data = resp.json()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error AI extract cheque_vide: {str(e)}")
                continue

            raw_content = ""
            for output_item in ai_data.get("output", []):
                for content_item in output_item.get("content", []):
                    if content_item.get("type") == "output_text":
                        raw_content = content_item.get("text", "")
                        break

            if not raw_content:
                continue

            try:
                result = json.loads(raw_content)
            except Exception:
                continue

            ste_code = result.get('ste', '')
            ste_record = False
            if ste_code:
                ste_record = self.env['finance2.ste'].search([('name', '=ilike', ste_code)], limit=1)
                
            perso_name = result.get('personne', '')
            perso_record = False
            if perso_name:
                perso_record = self.env['finance2.personne'].search([('name', '=ilike', perso_name)], limit=1)
                if not perso_record:
                    perso_record = self.env['finance2.personne'].search([('name', 'ilike', perso_name)], limit=1)
            
            update_vals = {}
            final_chq = result.get('chq')
            final_ste_id = ste_record.id if ste_record else False

            if final_chq:
                update_vals['name'] = final_chq
            if final_ste_id:
                update_vals['ste_id'] = final_ste_id
            if perso_record:
                update_vals['personne_id'] = perso_record.id
            if result.get('date_emission'):
                update_vals['date_emission'] = result.get('date_emission')
            
            if update_vals:
                rec.sudo().write(update_vals)

            if not final_ste_id or not final_chq:
                from markupsafe import Markup
                rec.message_post(body=Markup(
                    "<div style='border-left:4px solid #ffc107;padding:8px 12px;background:#fff8e1;border-radius:4px;'>"
                    "<span style='color:#ffc107;font-size:15px;'><i class='fa fa-exclamation-triangle'></i>&nbsp;<b>IA : Extraction incomplète</b></span>"
                    f"<p style='margin:4px 0 0;'>L'IA n'a pas pu identifier le numéro de chèque ou la société ({ste_code}). Veuillez remplir ces champs manuellement.</p>"
                    "</div>"
                ))
            else:
                from markupsafe import Markup
                rec.message_post(body=Markup(
                    "<div style='border-left:4px solid #007bff;padding:8px 12px;background:#f8f9fa;border-radius:4px;'>"
                    "<span style='color:#007bff;font-size:15px;'><i class='fa fa-robot'></i>&nbsp;<b>IA : Chèque identifié</b></span>"
                    f"<p style='margin:4px 0 0;'>Le système a extrait le numéro <b>{final_chq}</b>, la société <b>{ste_code}</b>, la date d'émission <b>{result.get('date_emission', '')}</b> et la personne <b>{perso_name}</b>.</p>"
                    "</div>"
                ))

    def action_confirmer(self):
        for rec in self:
            rec.state = 'reserve'
            
    def action_remettre_finance(self):
        for rec in self:
            rec.state = 'brouillon'
            rec.remis_a_id = False
            rec.date_remise = False
            
    def action_mettre_actif(self):
        for rec in self:
            if not rec.remis_a_id:
                # Odoo will show a validation error if not present when required in view, 
                # but we can enforce it here too
                pass
            rec.state = 'actif'
            rec.date_remise = fields.Date.today()
            
    def action_cloturer(self):
        for rec in self:
            rec.state = 'cloture'
            
    def action_annuler(self):
        for rec in self:
            rec.state = 'annule'

    @api.model
    def _cron_check_actif_5_days(self):
        """Cron job that checks for cheques in 'actif' state for more than 5 days and sends a reminder."""
        limit_date = fields.Date.today() - timedelta(days=5)
        cheques = self.search([
            ('state', '=', 'actif'),
            ('date_remise', '<=', limit_date)
        ])
        for cheque in cheques:
            # Send message to chatter
            cheque.message_post(
                body=f"Rappel : Ce chèque est à l'état Actif depuis plus de 5 jours (remis le {cheque.date_remise}).",
                subtype_xmlid='mail.mt_note'
            )


class Finance2Repartition(models.Model):
    _name = 'finance2.repartition'
    _description = 'Répartition de Chèque'

    cheque_id = fields.Many2one('finance2.cheque', string='Chèque', required=True, ondelete='cascade')
    amount = fields.Float(string='Montant', required=True)
    serie_facture = fields.Char(string='Série de facture')
    bl = fields.Char(string='BL')
    journal = fields.Char(string='Journal')
