from odoo import models, fields

class TresorerieChqClient(models.Model):
    _name = 'tresorerie_chq.client'
    _description = 'Client (Trésorerie Chèques & Effets)'

    name = fields.Char(string='Nom', required=True)
    cin = fields.Char(string='CIN')
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='E-mail')
    address = fields.Text(string='Adresse')
    allow_no_date = fields.Boolean(
        string="Autoriser sans échéance",
        default=False,
        help="Si coché, permet d'enregistrer des chèques ou des effets sans date d'échéance pour ce client."
    )
    
    paiement_ids = fields.One2many('tresorerie_chq.paiement', 'client_id', string='Paiements')

