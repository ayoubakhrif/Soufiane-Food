from odoo import models, fields, api

class Kal3iyaAdvance(models.Model):
    _name = 'kal3iya.advance'
    _description = 'Avances'
    client_id = fields.Many2one('kal3iya.client', required=True)
    amount = fields.Float(string='Montant', required=True)
    date_paid = fields.Date(string='Date', required=True)
    driver_id = fields.Many2one('kal3iya.driver', string='Chauffeur')
    comment = fields.Text(string='Commentaire')
    payment_mode = fields.Selection([
        ('chq', 'CHQ'),
        ('espece', 'Espece'),
        ('virement', 'Virement'),
        ('versement', 'Versement'),
        ('charge', 'Charges'),
    ], string='Mode de paiement', tracking=True)