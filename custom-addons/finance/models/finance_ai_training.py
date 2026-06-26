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
                try:
                    import fitz  # PyMuPDF
                except ImportError:
                    from odoo.exceptions import UserError
                    raise UserError("La librairie 'PyMuPDF' n'est pas installée sur le serveur. Elle est indispensable pour convertir les PDF en images pour l'entraînement OpenAI. Veuillez exécuter 'pip install PyMuPDF'.")
                
                import base64
                pdf_bytes = base64.b64decode(rec.physical_cheque_id.cheque_copy_pdf)
                
                try:
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    if len(doc) > 0:
                        # Rendre la première page en image JPEG
                        page = doc.load_page(0)
                        # Zoom optionnel pour une meilleure qualité
                        matrix = fitz.Matrix(2.0, 2.0)
                        pix = page.get_pixmap(matrix=matrix)
                        img_bytes = pix.tobytes("jpeg")
                        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                        
                        user_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            }
                        })
                    doc.close()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Erreur de conversion PDF pour le chèque {rec.physical_cheque_id.id} : {e}")
                    # On ignore silencieusement pour ne pas bloquer l'export global, ou on pourrait lever une erreur.
            
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
