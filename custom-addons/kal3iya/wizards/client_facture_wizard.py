from odoo import models, fields, api
from odoo.exceptions import UserError

class ClientFactureWizard(models.TransientModel):
    _name = "client.facture.wizard"
    _description = "Assistant Facture Client"

    client_id = fields.Many2one("kal3iya.client", string="Client", required=True)
    week = fields.Char(string="Semaine (ex: 2025-W48)", required=True)

    def action_print(self):
        # Rechercher le rapport directement dans ir.actions.report
        report = self.env['ir.actions.report'].search([
            ('report_name', '=', 'kal3iya.client_facture_template'),
            ('model', '=', 'kal3iya.client')
        ], limit=1)
        
        if not report:
            raise UserError(
                "Le rapport 'Facture Client' n'est pas trouvé.\n"
                "Veuillez désinstaller puis réinstaller le module Kal3iya."
            )
        
        return report.report_action(
            self.client_id,
            data={'week': self.week}
        )