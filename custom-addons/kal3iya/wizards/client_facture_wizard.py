from odoo import models, fields, api

class ClientFactureWizard(models.TransientModel):
    _name = "client.facture.wizard"
    _description = "Assistant Facture Client"

    client_id = fields.Many2one("kal3iya.client", string="Client", required=True)
    week = fields.Char(string="Semaine (ex: 2025-W48)", required=True)

    def action_print(self):
        return self.env.ref("kal3iya.client_facture_report").report_action(
            self.client_id.id,
            data={'week': self.week}
        )
