from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaClientAdvance(models.Model):
    _name = 'casa_hanane.client.advance'
    _description = 'Avance Client Casa (Hanane)'

    client_id = fields.Many2one('casa_hanane.client', string='Client', required=True, ondelete='cascade')
    amount = fields.Float(string='Montant', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    payment_mode = fields.Selection([
        ('espece', 'Espèces'),
        ('cheque', 'Chèques'),
        ('charge', 'Charges'),
        ('transport', 'Transport'),
        ('autre', 'Autre'),
    ], string='Type', required=True, default='espece')
    
    comment = fields.Char(string='Commentaire')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Validé'),
    ], string='État', required=True, default='draft', readonly=True)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_("Vous ne pouvez pas supprimer une avance validée. Veuillez d'abord la remettre en brouillon."))
        return super(CasaClientAdvance, self).unlink()
