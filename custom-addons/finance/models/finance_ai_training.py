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
