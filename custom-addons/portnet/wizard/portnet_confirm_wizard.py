from odoo import models, fields

class PortnetConfirmWizard(models.TransientModel):
    _name = 'portnet.confirm.wizard'
    _description = 'Confirmation de domiciliation'

    entry_id = fields.Many2one('portnet.entry', string='Entrée Portnet', required=True)
    message = fields.Text(string='Message', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        # Call the confirmation action on the entry, explicitly passing context
        # to skip the wizard popup check
        return self.entry_id.with_context(bypass_valeur_wizard=True).action_domicilier()
