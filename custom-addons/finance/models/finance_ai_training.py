# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FinanceAITraining(models.Model):
    _name = 'finance.ai.training'
    _description = 'AI Training Data Collection'
    _order = 'create_date desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, index=True, default=lambda self: 'New')
    source = fields.Selection([
        ('whatsapp', 'WhatsApp Bot'),
        ('physical_cheque', 'Chèque Physique UI')
    ], string='Source', required=True)
    
    prompt_text = fields.Text(string='Prompt Utilisé', readonly=True)
    ai_result_json = fields.Text(string='Résultat Brut IA (JSON)', readonly=True)
    final_result_json = fields.Text(string='Résultat Final Validé (JSON)')
    
    is_corrected = fields.Boolean(string='Corrigé par Utilisateur', default=False, readonly=True)
    
    datacheque_id = fields.Many2one('datacheque', string='Répartition (Datacheque)', ondelete='set null')
    physical_cheque_id = fields.Many2one('finance.cheque.physical', string='Chèque Physique', ondelete='set null')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('finance.ai.training') or 'New'
        return super(FinanceAITraining, self).create(vals)

    def action_export_openai_jsonl(self):
        import json
        import base64

        jsonl_lines = []
        for rec in self:
            if not rec.prompt_text or not rec.final_result_json:
                continue
            
            # Format attendu par OpenAI Chat Completion Fine-tuning
            message_obj = {
                "messages": [
                    {
                        "role": "system",
                        "content": "Vous êtes un assistant comptable spécialisé dans l'importation et la finance. Retournez UNIQUEMENT un objet JSON valide, sans formatage markdown, sans explications."
                    }
                ]
            }

            user_content = []
            
            # Injection dynamique du PDF si c'est un chèque physique
            if rec.source == 'physical_cheque' and rec.physical_cheque_id and rec.physical_cheque_id.cheque_copy_pdf:
                # Convert the binary field to base64 string
                import base64
                pdf_b64 = rec.physical_cheque_id.cheque_copy_pdf.decode('utf-8')
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:application/pdf;base64,{pdf_b64}"
                    }
                })
            
            # Ajouter le texte du prompt
            user_content.append({
                "type": "text",
                "text": rec.prompt_text
            })

            message_obj["messages"].append({
                "role": "user",
                "content": user_content
            })

            message_obj["messages"].append({
                "role": "assistant",
                "content": rec.final_result_json
            })
            
            jsonl_lines.append(json.dumps(message_obj, ensure_ascii=False))
            
        if not jsonl_lines:
            from odoo.exceptions import ValidationError
            raise ValidationError("Aucune donnée valide à exporter parmi les enregistrements sélectionnés.")

        file_content = "\n".join(jsonl_lines)
        file_content_b64 = base64.b64encode(file_content.encode('utf-8'))

        attachment = self.env['ir.attachment'].create({
            'name': 'openai_finetune_dataset.jsonl',
            'type': 'binary',
            'datas': file_content_b64,
            'store_fname': 'openai_finetune_dataset.jsonl',
            'res_model': self._name,
            'res_id': self.ids[0] if self.ids else False,
            'mimetype': 'application/jsonl'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
