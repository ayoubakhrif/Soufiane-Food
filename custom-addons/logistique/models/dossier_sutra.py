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
