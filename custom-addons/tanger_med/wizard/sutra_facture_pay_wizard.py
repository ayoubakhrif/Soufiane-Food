from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SutraFacturePayWizard(models.TransientModel):
    _name = 'sutra.facture.pay.wizard'
    _description = 'Wizard pour payer les factures SUTRA'

    ste_id = fields.Many2one('finance2.ste', string='Societe', required=True)
    benif_id = fields.Many2one('finance2.benif', string='Beneficiaire', required=True)
    amount_total = fields.Float(string='Montant du Cheque', required=True)
    cheque_number = fields.Char(string='Numero du Cheque', required=True)
    date_emission = fields.Date(string="Date d'emission", required=True, default=fields.Date.context_today)
    journal = fields.Char(string='Carnet / Journal')
    facture_ids = fields.Many2many('sutra.facture', string='Factures a payer')

    @api.model
    def default_get(self, fields_list):
        res = super(SutraFacturePayWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return res

        factures = self.env['sutra.facture'].browse(active_ids)
        
        # Verify they are all non_paye
        if any(f.state != 'non_paye' for f in factures):
            raise UserError("Vous ne pouvez selectionner que des factures non payees.")

        total = sum(f.amount for f in factures)
        res['amount_total'] = total
        res['facture_ids'] = [(6, 0, active_ids)]

        # Try to infer 'ste_id' from the first logistics dossier
        first_facture = factures[0]
        if first_facture.sutra_id and first_facture.sutra_id.logistics_id and first_facture.sutra_id.logistics_id.ste_id:
            log_ste = first_facture.sutra_id.logistics_id.ste_id
            fin_ste = self.env['finance2.ste'].search([('name', '=', log_ste.name)], limit=1)
            if fin_ste:
                res['ste_id'] = fin_ste.id

        return res

    def action_generate_cheque(self):
        if not self.facture_ids:
            raise UserError("Aucune facture selectionnee.")

        # Create the cheque in finance2
        cheque_vals = {
            'type': 'cheque',
            'name': self.cheque_number,
            'ste_id': self.ste_id.id,
            'benif_id': self.benif_id.id,
            'amount_total': self.amount_total,
            'date_emission': self.date_emission,
            'journal': self.journal,
        }
        
        new_cheque = self.env['finance2.cheque'].create(cheque_vals)

        # Create one global repartition line for the total amount
        self.env['finance2.repartition'].create({
            'cheque_id': new_cheque.id,
            'amount': self.amount_total,
            'type': 'surestarie', # Using surestarie as default, or magasinage
            'dossier_name': 'Paiement SUTRA Groupé'
        })

        # Link factures and change state
        self.facture_ids.write({
            'cheque_id': new_cheque.id,
            'state': 'encours'
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cheque Genere',
                'message': f"Le cheque {self.cheque_number} a ete cree avec succes.",
                'type': 'success',
                'sticky': False,
            }
        }
