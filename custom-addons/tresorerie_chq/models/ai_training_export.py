from odoo import models, fields, api
import json
import base64

class TresorerieChqAITrainingExport(models.TransientModel):
    _name = 'tresorerie_chq.ai.training.export'
    _description = "Assistant d'export pour le Fine-Tuning IA"

    export_type = fields.Selection([
        ('corrected', 'Uniquement les données corrigées (Option A)'),
        ('all', 'Toutes les données (Option B)'),
    ], string='Type d\'export', required=True, default='all',
        help="Il est souvent recommandé de fournir un mix (Toutes les données) pour ne pas que l'IA oublie les cas simples.")

    file_data = fields.Binary(string='Fichier JSONL', readonly=True)
    file_name = fields.Char(string='Nom du fichier', readonly=True)
    state = fields.Selection([('choose', 'Choix'), ('get', 'Terminé')], default='choose')

    def action_export(self):
        url = f'/tresorerie_chq/export_ai_data?export_type={self.export_type}'
        
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

