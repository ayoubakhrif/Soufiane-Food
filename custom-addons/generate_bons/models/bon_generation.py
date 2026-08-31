from odoo import models, fields, api
from datetime import datetime

class BonGeneration(models.Model):
    _name = 'bon.generation'
    _description = 'Génération des bons'
    _order = 'date desc, id desc'

    company_id = fields.Many2one('core.ste', string='Société', required=True)
    name = fields.Char(string='Numéro', required=True, copy=False, readonly=True, default='/')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    reference = fields.Char(string='Référence')
    
    line_ids = fields.One2many('bon.generation.line', 'bon_id', string='Lignes')
    
    total_ttc = fields.Float(string='Total Montant TTC', compute='_compute_total', store=True)
    
    @api.depends('line_ids.montant_ttc')
    def _compute_total(self):
        for record in self:
            record.total_ttc = sum(record.line_ids.mapped('montant_ttc'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company_id = vals.get('company_id')
                date_val = vals.get('date', fields.Date.context_today(self))
                
                seq_code = f'bon.generation.{company_id}'
                seq = self.env['ir.sequence'].search([('code', '=', seq_code)], limit=1)
                if not seq:
                    seq = self.env['ir.sequence'].sudo().create({
                        'name': f'Sequence Bon Société {company_id}',
                        'code': seq_code,
                        'prefix': '%(y)s%(month)s',
                        'padding': 6,
                        'company_id': False,
                    })
                
                vals['name'] = seq.next_by_id(sequence_date=date_val)
        return super().create(vals_list)

class BonGenerationLine(models.Model):
    _name = 'bon.generation.line'
    _description = 'Ligne de bon'

    bon_id = fields.Many2one('bon.generation', string='Bon', required=True, ondelete='cascade')
    article_id = fields.Many2one('bon.article', string='Article', required=True)
    name = fields.Char(string='Désignation', related='article_id.name', store=True)
    qte = fields.Float(string='Qté', default=1.0, required=True)
    pu = fields.Float(string='Px U, T', required=True)
    montant_ttc = fields.Float(string='Montant TTC', compute='_compute_montant', store=True)

    @api.onchange('article_id')
    def _onchange_article_id(self):
        if self.article_id:
            self.pu = self.article_id.pu

    @api.depends('qte', 'pu')
    def _compute_montant(self):
        for line in self:
            line.montant_ttc = line.qte * line.pu
