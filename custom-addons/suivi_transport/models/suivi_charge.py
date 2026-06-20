from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SuiviCharge(models.Model):
    _name = 'suivi.charge'
    _description = 'Charge et Entretien Véhicule'
    _order = 'date desc, id desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='/')
    chauffeur_id = fields.Many2one('suivi.chauffeur', string='Chauffeur', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    
    type_charge = fields.Selection([
        ('pneus', 'Pneus'),
        ('vidange', 'Vidange'),
        ('mecanique', 'Mécanique'),
        ('assurance', 'Assurance'),
        ('vignette', 'Vignette'),
        ('visite', 'La visite'),
        ('autres', 'Autres')
    ], string='Type de Charge', required=True)
    
    montant = fields.Float(string='Montant (MAD)', required=True)
    facture = fields.Binary(string='Facture / Reçu', attachment=True)
    facture_name = fields.Char(string='Nom du fichier')
    note = fields.Text(string='Description / Remarques')

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('suivi.charge') or '/'
        return super(SuiviCharge, self).create(vals)

    @api.constrains('montant')
    def _check_montant_positive(self):
        for rec in self:
            if rec.montant <= 0:
                raise ValidationError(_("Le montant de la charge doit être strictement positif."))
