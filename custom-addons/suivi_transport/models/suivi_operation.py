from odoo import models, fields, api

class SuiviOperation(models.Model):
    _name = 'suivi.operation'
    _description = 'Opération Suivi Transport'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    chauffeur_id = fields.Many2one('suivi.chauffeur', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    lot = fields.Char(string='LOT')
    montant = fields.Float(string='Montant')
    credit = fields.Float(string='Crédit', help="Si la commande n'est pas payée")
    payer_id = fields.Many2one('suivi.client', string='Qui a payé')

    line_ids = fields.One2many('suivi.operation.line', 'operation_id', string='Détails des opérations')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('suivi.operation') or '/'
        return super(SuiviOperation, self).create(vals)

class SuiviOperationLine(models.Model):
    _name = 'suivi.operation.line'
    _description = 'Ligne Opération Suivi Transport'

    operation_id = fields.Many2one('suivi.operation', string='Opération', required=True, ondelete='cascade')
    client_id = fields.Many2one('suivi.client', string='Client')
    article_id = fields.Many2one('company.article', string='Article')
    lot = fields.Char(string='LOT')
