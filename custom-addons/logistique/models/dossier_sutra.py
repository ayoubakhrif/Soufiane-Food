from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LogistiqueDossierSutra(models.Model):
    _name = 'logistique.dossier.sutra'
    _description = 'Ligne Sutra Dossier Logistique'

    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier',
        compute='_compute_dossier_id',
        store=True,
        readonly=False,
        ondelete='cascade'
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

    @api.depends('entry_id')
    def _compute_dossier_id(self):
        for rec in self:
            if rec.entry_id:
                rec.dossier_id = rec.entry_id.dossier_id
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
        ('assurance', 'Assurance'),
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

    @api.constrains('entry_id', 'amount', 'type', 'date', 'beneficiary_id')
    def _check_entry_status(self):
        for rec in self:
            if rec.entry_id and rec.entry_id.status == 'in_progress':
                raise ValidationError("Vous ne pouvez pas ajouter ou modifier des lignes Sutra tant que le dossier est 'En cours'. Veuillez d'abord le passer en 'Gate Out'.")
