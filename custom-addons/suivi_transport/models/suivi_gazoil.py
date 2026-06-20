from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SuiviGazoil(models.Model):
    _name = 'suivi.gazoil'
    _description = 'Suivi Gazoil'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    chauffeur_id = fields.Many2one('suivi.chauffeur', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    montant = fields.Float(string='Montant Payé (MAD)', required=True)
    prix_litre = fields.Float(string='Prix par Litre (MAD)', required=True)
    litres = fields.Float(string='Nombre de Litres', compute='_compute_litres', store=True)
    
    kilometrage = fields.Float(string='Kilométrage Actuel', required=True)
    
    note = fields.Text(string='Remarques')

    @api.depends('montant', 'prix_litre')
    def _compute_litres(self):
        for rec in self:
            if rec.prix_litre > 0:
                rec.litres = rec.montant / rec.prix_litre
            else:
                rec.litres = 0.0

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('suivi.gazoil') or '/'
        return super(SuiviGazoil, self).create(vals)

    @api.constrains('montant', 'prix_litre', 'kilometrage')
    def _check_positive_values(self):
        for rec in self:
            if rec.montant <= 0:
                raise ValidationError(_("Le montant doit être strictement positif."))
            if rec.prix_litre <= 0:
                raise ValidationError(_("Le prix par litre doit être strictement positif."))
            if rec.kilometrage < 0:
                raise ValidationError(_("Le kilométrage ne peut pas être négatif."))
