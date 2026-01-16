from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LogisticsEntry(models.Model):
    _inherit = 'logistique.entry'

    contract_id = fields.Many2one('achat.contract', string='Contract', domain="[('state', '=', 'open')]")
    free_time_negotiated = fields.Integer(string='Negotiated Free Time')

    
    # Document Link
    document_ids = fields.One2many('logistique.entry.document', 'entry_id', string='Documents')

    display_name = fields.Char(compute='_compute_display_name') # Just to ensure we have it if needed

    def action_confirm_purchase(self):
        # Security Check: Only Purchase Managers can confirm
        if not self.env.user.has_group('achat.group_purchase_manager'):
            raise ValidationError("Seul le responsable Achat (ou Admin) peut confirmer un dossier.")
        return super(LogisticsEntry, self).action_confirm_purchase()

    @api.onchange('contract_id')
    def _onchange_contract_id(self):
        if self.contract_id:
            self.contract_num = self.contract_id.name
            self.supplier_id = self.contract_id.supplier_id
            self.ste_id = self.contract_id.ste_id
            self.article_id = self.contract_id.article_id
            self.incoterm = self.contract_id.incoterm
            self.details = self.contract_id.details
            self.origin = self.contract_id.origin
            self.free_time_negotiated = self.contract_id.free_time_negotiated
            # Pre-fill actual free time with negotiated value
            self.free_time = self.contract_id.free_time_negotiated
            if self.contract_id.weight_total:
                self.weight = self.contract_id.weight_total # Optional sync, user might update per shipment
