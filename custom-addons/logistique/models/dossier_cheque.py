from odoo import models, fields, api

class LogistiqueDossierCheque(models.Model):
    _name = 'logistique.dossier.cheque'
    _description = 'Chèque Dossier Logistique'

    dossier_id = fields.Many2one('logistique.dossier', string='Dossier', required=True, ondelete='cascade')
    cheque_serie = fields.Char(string='Série Chèque', required=True, size=7)
    date = fields.Date(string='Date')
    beneficiary_id = fields.Many2one('logistique.shipping', string='Bénéficiaire')
    amount = fields.Float(string='Montant', required=True)
    ste_id = fields.Many2one('logistique.ste', string='Société', required=True)
    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('fret', 'FRET'),
        ('surestarie', 'Surestarie'),
    ], string='Type')

    @api.model
    def default_get(self, fields_list):
        res = super(LogistiqueDossierCheque, self).default_get(fields_list)

        dossier_id = self.env.context.get('default_dossier_id')
        if dossier_id:
            dossier = self.env['logistique.dossier'].browse(dossier_id)
            # Find the ste_id from the first linked logistique.entry
            if dossier.entry_ids:
                res.update({
                    'ste_id': dossier.entry_ids[0].ste_id.id,
                })
        return res
