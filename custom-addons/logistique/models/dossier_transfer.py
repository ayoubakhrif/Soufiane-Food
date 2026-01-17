from odoo import models, fields, api

class LogistiqueDossierTransfer(models.Model):
    _name = 'logistique.dossier.transfer'
    _description = 'Virement Dossier Logistique'

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
        compute='_compute_ste_id',
        store=True,
        readonly=False
    )

    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier',
        compute='_compute_dossier_id',
        store=True
    )

    @api.depends('entry_id')
    def _compute_dossier_id(self):
        for rec in self:
            rec.dossier_id = rec.entry_id.dossier_id if rec.entry_id else False

    
    @api.depends('dossier_id')
    def _compute_ste_id(self):
        for rec in self:
            if rec.dossier_id:
                rec.ste_id = rec.dossier_id.ste_id

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
