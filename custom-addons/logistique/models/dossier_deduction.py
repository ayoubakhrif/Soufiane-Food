from odoo import models, fields, api

class LogistiqueDossierDeduction(models.Model):
    _name = 'logistique.dossier.deduction'
    _description = 'Déduction Dossier Logistique'

    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier',
        required=True,
        ondelete='cascade'
    )

    entry_id = fields.Many2one(
        'logistique.entry',
        string='Entrée Logistique',
        ondelete='cascade'
    )

    date = fields.Date(string='Date', required=True)
    amount = fields.Float(string='Montant', required=True)

    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('surestarie', 'Surestarie'),
        ('fret', 'FRET'),
    ], string='Type', required=True)


    beneficiary_id = fields.Many2one(
        'logistique.shipping',
        string='Bénéficiaire',
        required=True
    )

    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        required=True,
        readonly=True
    )

    # ---------- Auto-fill ----------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        entry_id = self.env.context.get('default_entry_id')
        if entry_id:
            entry = self.env['logistique.entry'].browse(entry_id)
            res.update({
                'entry_id': entry.id,
                'dossier_id': entry.dossier_id.id if entry.dossier_id else False,
                'ste_id': entry.ste_id.id if entry.ste_id else False,
                'beneficiary_id': entry.shipping_id.id if entry.shipping_id else False,
            })
        return res
