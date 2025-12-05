from odoo import models, fields, api

class ClientFactureWizard(models.TransientModel):
    _name = "client.facture.wizard"
    _description = "Assistant Facture Client"

    client_id = fields.Many2one("kal3iya.client", string="Client", required=True)
    week = fields.Char(string="Semaine (ex: 2025-W48)", required=True)

    def action_print(self):
        client = self.client_id
        return self.env.ref("kal3iya.action_report_client_facture").report_action(
            client,
            data={'week': self.week}
        )
