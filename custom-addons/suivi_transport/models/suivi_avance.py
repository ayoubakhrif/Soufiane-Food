from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SuiviAvance(models.Model):
    _name = 'suivi.avance'
    _description = 'Avance Chauffeur'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    chauffeur_id = fields.Many2one('suivi.chauffeur', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    montant = fields.Float(string='Montant (MAD)', required=True)
    note = fields.Text(string='Remarques')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('suivi.avance') or '/'
        return super(SuiviAvance, self).create(vals)

    @api.constrains('montant')
    def _check_montant_positive(self):
        for rec in self:
            if rec.montant <= 0:
                raise ValidationError(_("Le montant de l'avance doit être strictement positif."))
