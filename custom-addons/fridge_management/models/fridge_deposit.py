from odoo import models, fields, api

class FridgeDeposit(models.Model):
    _name = 'fridge.deposit'
    _description = 'Dossier de Dépôt Client'

    name = fields.Char(string="Référence", required=True, copy=False, readonly=True, default=lambda self: 'Nouveau')
    partner_id = fields.Many2one('res.partner', string="Client", required=True)
    description = fields.Char(string="Marchandise / Description", required=True)
    requested_tonnes = fields.Float(string="Tonnage Prévu (Tonnes)", required=True)
    requested_temp = fields.Char(string="Température Souhaitée")
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('active', 'En cours de stockage'),
        ('done', 'Clôturé')
    ], string="Statut", default='draft', tracking=True)

    ledger_ids = fields.One2many('fridge.ledger', 'deposit_id', string="Mouvements (Audit Ledger)")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('fridge.deposit') or 'Nouveau'
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            record.state = 'active'
            
    def action_done(self):
        for record in self:
            record.state = 'done'
