from odoo import models, fields, api

class LogistiqueDossierCheque(models.Model):
    _name = 'logistique.dossier.cheque'
    _description = 'Chèque Dossier Logistique'

    cheque_serie = fields.Char(string='Série Chèque', required=True, size=7)
    date = fields.Date(string='Date')
    beneficiary_id = fields.Many2one('logistique.shipping', string='Bénéficiaire')
    amount = fields.Float(string='Montant', required=True)
    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        related='dossier_id.ste_id',
        store=True,
        readonly=True
    )
    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('fret', 'FRET'),
        ('surestarie', 'Surestarie'),
    ], string='Type')
    entry_id = fields.Many2one(
        'logistique.entry',
        string='Entrée Logistique',
        required=True,
        ondelete='cascade'
    )
    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier',
        compute='_compute_dossier_id',
        store=True,
        readonly=True
    )

    @api.depends('entry_id')
    def _compute_dossier_id(self):
        for rec in self:
            rec.dossier_id = rec.entry_id.dossier_id if rec.entry_id else False


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        entry_id = self.env.context.get('default_entry_id')
        if entry_id:
            entry = self.env['logistique.entry'].browse(entry_id)
            res.update({
                'ste_id': entry.ste_id.id if entry.ste_id else False,
                'dossier_id': entry.dossier_id.id if entry.dossier_id else False,
            })
        return res

    @api.onchange('entry_id')
    def _onchange_entry_id(self):
        for rec in self:
            if rec.entry_id:
                rec.ste_id = rec.entry_id.ste_id
                rec.dossier_id = rec.entry_id.dossier_id
