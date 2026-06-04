from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CasaClientAdvance(models.Model):
    _name = 'casa.client.advance'
    _description = 'Avance Client Casa'
    _order = 'state desc, id desc'

    client_id = fields.Many2one('casa.client', string='Client', required=True, ondelete='cascade')
    amount = fields.Float(string='Montant', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    payment_mode = fields.Selection([
        ('espece', 'Espèces'),
        ('versement', 'Versement'),
        ('virement', 'Virement'),
        ('cheque', 'Chèques'),
        ('charge', 'Charges'),
        ('transport', 'Transport'),
        ('autre', 'Autre'),
    ], string='Type', required=True, default='espece')
    
    ville = fields.Selection([
        ('tanger', 'Tanger'),
        ('casa', 'Casa'),
        ('kenitra', 'Kenitra'),
        ('agadir', 'Agadir'),
        ('marrakech', 'Marrakech'),
    ], string='Ville')

    comment = fields.Char(string='Commentaire')
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Validé'),
        ('cancelled', 'Annulé'),
    ], string='État', required=True, default='draft', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('payment_mode') == 'transport' and not self.env.context.get('is_transport_operation'):
            raise UserError(_("Les avances de type 'Transport' ne peuvent être créées automatiquement que depuis la validation des opérations de transport Tanger."))
        return super().create(vals)

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'

    def write(self, vals):
        if vals.get('payment_mode') == 'transport' and not self.env.context.get('is_transport_operation'):
            raise UserError(_("Les avances de type 'Transport' ne peuvent être créées automatiquement que depuis la validation des opérations de transport Tanger."))
        for rec in self:
            if not self.env.context.get('is_transport_operation') and rec.state == 'confirmed' and any(f != 'state' for f in vals):
                 raise UserError(_("Vous ne pouvez pas modifier une avance validée. Veuillez d'abord la remettre en brouillon."))
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'confirmed':
                raise UserError(_("Vous ne pouvez pas supprimer une avance validée. Veuillez d'abord la remettre en brouillon."))
        return super().unlink()
