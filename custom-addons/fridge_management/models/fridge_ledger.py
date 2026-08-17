from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FridgeLedger(models.Model):
    _name = 'fridge.ledger'
    _description = 'Audit Ledger des Mouvements'
    _order = 'date desc, id desc'

    name = fields.Char(string="Description de l'opération")
    date = fields.Datetime(string="Date de l'opération", default=fields.Datetime.now, required=True)
    deposit_id = fields.Many2one('fridge.deposit', string="Dossier Client", required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='deposit_id.partner_id', string="Client", store=True)
    
    fridge_id = fields.Many2one('fridge.equipment', string="Frigo Concerné", required=True)
    
    operation_type = fields.Selection([
        ('in', 'Entrée (Check-in)'),
        ('out', 'Sortie (Check-out)')
    ], string="Type de Mouvement", required=True)
    
    tonnes = fields.Float(string="Quantité (Tonnes)", required=True)
    user_id = fields.Many2one('res.users', string="Employé", default=lambda self: self.env.user)

    @api.constrains('tonnes')
    def _check_tonnes(self):
        for record in self:
            if record.tonnes <= 0:
                raise ValidationError("La quantité manipulée doit être strictement positive.")
