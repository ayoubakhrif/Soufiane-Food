from odoo import models, fields, api

class LogistiqueDossierSutra(models.Model):
    _name = 'logistique.dossier.sutra'
    _description = 'Ligne Sutra Dossier Logistique'

    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier',
        ondelete='cascade',
        required=True
    )
    entry_id = fields.Many2one(
        'logistique.entry',
        string='Entrée Logistique',
        ondelete='cascade'
    )

    @api.model
    def default_get(self, fields_list):
        res = super(LogistiqueDossierSutra, self).default_get(fields_list)
        if 'dossier_id' in fields_list and not res.get('dossier_id'):
            entry_id = self.env.context.get('default_entry_id')
            if entry_id:
                entry = self.env['logistique.entry'].browse(entry_id)
                if entry.exists():
                    res['dossier_id'] = entry.dossier_id.id
        return res

    @api.onchange('entry_id')
    def _onchange_entry_id(self):
        if self.entry_id and self.entry_id.dossier_id:
            self.dossier_id = self.entry_id.dossier_id
    amount = fields.Float(string='Montant', required=True)
    invoice = fields.Char(string='Facture')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    user_id = fields.Many2one(
        'res.users',
        string='Saisi par',
        default=lambda self: self.env.user,
        readonly=True
    )
    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('surestarie', 'Surestarie'),
        ('fret', 'FRET'),
        ('autres', 'Autres factures'),
    ], string='Type')
    beneficiary_id = fields.Many2one(
        'logistique.shipping',
        string='Bénéficiaire'
    )
    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        compute='_compute_ste_id',
        store=True
    )

    @api.depends('dossier_id')
    def _compute_ste_id(self):
        for rec in self:
            rec.ste_id = rec.dossier_id.ste_id if rec.dossier_id else False
