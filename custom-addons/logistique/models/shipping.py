from odoo import models, fields

class LogistiqueShipping(models.Model):
    _name = 'logistique.shipping'
    _description = 'Compagnie Maritime'

    name = fields.Char(string='Nom', required=True)
    attestation_email = fields.Char(string="Email d'attestation", help="Adresse email utilisée pour envoyer la demande d'attestation d'escale")
