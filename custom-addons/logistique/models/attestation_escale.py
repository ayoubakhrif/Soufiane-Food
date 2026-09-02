from odoo import models, fields, api
from datetime import date

class LogisticsEntryAttestation(models.Model):
    _inherit = 'logistique.entry'

    attestation_state = fields.Selection([
        ('not_requested', 'Non demandée'),
        ('requested', 'Demandée'),
        ('received', 'Reçue')
    ], string="Statut Attestation", default='not_requested', tracking=True)

    attestation_request_date = fields.Date(string="Date demande", tracking=True)
    attestation_receive_date = fields.Date(string="Date réception", tracking=True)

    attestation_file = fields.Binary(string="Fichier Attestation", attachment=True)
    attestation_file_name = fields.Char(string="Nom du fichier")

    def action_request_attestation(self):
        for rec in self:
            rec.attestation_state = 'requested'
            if not rec.attestation_request_date:
                rec.attestation_request_date = date.today()

    def action_receive_attestation(self):
        for rec in self:
            rec.attestation_state = 'received'
            if not rec.attestation_receive_date:
                rec.attestation_receive_date = date.today()
