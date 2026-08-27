from odoo import models, fields, api
from odoo.exceptions import ValidationError

class TvaDeclaration(models.Model):
    _name = 'tva.declaration'
    _description = 'Déclaration mensuelle de TVA'
    _rec_name = 'name'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    
    mois_tva = fields.Selection([
        ('01', 'Janvier'), ('02', 'Février'), ('03', 'Mars'), ('04', 'Avril'),
        ('05', 'Mai'), ('06', 'Juin'), ('07', 'Juillet'), ('08', 'Août'),
        ('09', 'Septembre'), ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
    ], string='Mois TVA', required=True)
    
    def _get_years(self):
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    annee_tva = fields.Selection(selection='_get_years', string='Année TVA', default=lambda self: str(fields.Date.today().year), required=True)
    
    tva_encaissee = fields.Float(string='TVA Encaissée', compute='_compute_tva_totals', store=True, help="Total de la TVA sur les encaissements du mois.")
    tva_decaissee = fields.Float(string='TVA Décaissée', compute='_compute_tva_totals', store=True, help="Total de la TVA sur les décaissements du mois.")
    credit_tva_passe = fields.Float(string='Crédit de TVA précédent', default=0.0)
    
    tva_a_payer = fields.Float(string='TVA à payer / (Crédit)', compute='_compute_tva_a_payer', store=True, help="TVA Encaissée - TVA Décaissée - Crédit passé. Si négatif, il s'agit d'un nouveau crédit de TVA.")

    @api.depends('mois_tva', 'annee_tva')
    def _compute_name(self):
        for record in self:
            if record.mois_tva and record.annee_tva:
                record.name = f"Déclaration TVA - {record.mois_tva}/{record.annee_tva}"
            else:
                record.name = "Nouvelle déclaration"

    @api.depends('mois_tva', 'annee_tva')
    def _compute_tva_totals(self):
        for record in self:
            if record.mois_tva and record.annee_tva:
                encaissements = self.env['tva.encaissement'].search([
                    ('mois_tva', '=', record.mois_tva),
                    ('annee_tva', '=', record.annee_tva)
                ])
                record.tva_encaissee = sum(encaissements.mapped('amount_tva'))
                
                decaissements = self.env['tva.decaissement'].search([
                    ('mois_tva', '=', record.mois_tva),
                    ('annee_tva', '=', record.annee_tva)
                ])
                record.tva_decaissee = sum(decaissements.mapped('amount_tva'))
            else:
                record.tva_encaissee = 0.0
                record.tva_decaissee = 0.0

    @api.depends('tva_encaissee', 'tva_decaissee', 'credit_tva_passe')
    def _compute_tva_a_payer(self):
        for record in self:
            record.tva_a_payer = record.tva_encaissee - record.tva_decaissee - record.credit_tva_passe

    @api.constrains('mois_tva', 'annee_tva')
    def _check_unique_declaration(self):
        for record in self:
            domain = [
                ('mois_tva', '=', record.mois_tva),
                ('annee_tva', '=', record.annee_tva),
                ('id', '!=', record.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError("Une déclaration pour ce mois et cette année existe déjà.")
