from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import calendar

class TvaDecaissement(models.Model):
    _name = 'tva.decaissement'
    _description = 'Déclaration de décaissement'
    _rec_name = 'invoice_number'

    invoice_number = fields.Char(string='N° facture', required=True)

    amount_ht = fields.Float(string='Montant HT')
    tva_rate = fields.Float(string='Taux de TVA (%)')
    amount_tva = fields.Float(string='Montant de la TVA', compute='_compute_amounts', store=True)
    amount_ttc = fields.Float(string='Montant TTC', compute='_compute_amounts', store=True)
    
    fournisseur_id = fields.Many2one('tva.fournisseur', string='Nom ou raison sociale', required=True)
    fournisseur_if = fields.Char(related='fournisseur_id.if_number', string='IF de fournisseur', readonly=True)
    fournisseur_ice = fields.Char(related='fournisseur_id.ice_number', string='ICE de fournisseur', readonly=True)
    
    payment_method = fields.Selection([
        ('virement', 'Virement'),
        ('prelevement', 'Prélevement'),
        ('cheque', 'Chèque'),
        ('versement', 'Versement'),
        ('espece', 'Espèce')
    ], string='Mode de paiement')
    
    invoice_date = fields.Date(string='Date facture')
    payment_date = fields.Date(string='Date paiement')
    
    mois_tva = fields.Selection([
        ('01', 'Janvier'), ('02', 'Février'), ('03', 'Mars'), ('04', 'Avril'),
        ('05', 'Mai'), ('06', 'Juin'), ('07', 'Juillet'), ('08', 'Août'),
        ('09', 'Septembre'), ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
    ], string='Mois TVA')
    
    def _get_years(self):
        current_year = fields.Date.today().year
        return [(str(y), str(y)) for y in range(current_year - 5, current_year + 5)]

    annee_tva = fields.Selection(selection='_get_years', string='Année TVA', default=lambda self: str(fields.Date.today().year))
    
    tva_code = fields.Char(string='Code TVA')
    prorata = fields.Float(string='Prorata (%)')

    is_acompte = fields.Boolean(string='Est un acompte', default=False)

    @api.depends('amount_ht', 'tva_rate')
    def _compute_amounts(self):
        for record in self:
            record.amount_tva = record.amount_ht * (record.tva_rate / 100.0)
            record.amount_ttc = record.amount_ht + record.amount_tva

    @api.constrains('invoice_number', 'fournisseur_id', 'is_acompte')
    def _check_unique_invoice(self):
        for record in self:
            if record.invoice_number and record.fournisseur_id and not record.is_acompte:
                domain = [
                    ('invoice_number', '=', record.invoice_number),
                    ('fournisseur_id', '=', record.fournisseur_id.id),
                    ('is_acompte', '=', False),
                    ('id', '!=', record.id)
                ]
                if self.search_count(domain) > 0:
                    raise ValidationError("Une facture principale avec ce numéro et ce même fournisseur existe déjà.")

    @api.onchange('invoice_number', 'fournisseur_id', 'is_acompte')
    def _onchange_invoice_acompte(self):
        if self.invoice_number and self.fournisseur_id and self.is_acompte:
            domain = [
                ('invoice_number', '=', self.invoice_number),
                ('fournisseur_id', '=', self.fournisseur_id.id)
            ]
            if self._origin.id:
                domain.append(('id', '!=', self._origin.id))
                
            existing_records = self.search(domain)
            
            if existing_records:
                parent_invoices = existing_records.filtered(lambda r: not r.is_acompte)
                acomptes = existing_records.filtered(lambda r: r.is_acompte)
                
                msg = "Attention, vous créez un acompte pour une facture (ou acompte) existante.\n\n"
                if parent_invoices:
                    msg += f"- Facture mère trouvée : {parent_invoices[0].amount_ttc} TTC (Enregistrée le {parent_invoices[0].create_date.strftime('%Y-%m-%d') if parent_invoices[0].create_date else 'N/A'})\n"
                if acomptes:
                    msg += "- Acomptes précédents trouvés :\n"
                    for ac in acomptes:
                        msg += f"  * Montant : {ac.amount_ttc} TTC\n"
                        
                return {
                    'warning': {
                        'title': 'Acompte détecté',
                        'message': msg
                    }
                }

    @api.constrains('invoice_date', 'payment_date', 'fournisseur_id')
    def _check_payment_date(self):
        for record in self:
            if record.invoice_date and record.payment_date and record.fournisseur_id:
                convention = record.fournisseur_id.convention
                
                if convention == '120':
                    limit = 120
                elif convention == '90':
                    limit = 90
                else:
                    # 'none' ou non défini -> 60 jours
                    limit = 60
                    
                diff = (record.payment_date - record.invoice_date).days
                if diff >= limit:
                    raise ValidationError(f"La facture doit être payée avant {limit} jours (Convention applicable). L'écart actuel est de {diff} jours.")

    @api.constrains('mois_tva', 'annee_tva', 'payment_date', 'invoice_date')
    def _check_tva_dates(self):
        for record in self:
            if record.mois_tva and record.annee_tva:
                tva_start = fields.Date.from_string(f"{record.annee_tva}-{record.mois_tva}-01")
                last_day = calendar.monthrange(tva_start.year, tva_start.month)[1]
                tva_end = tva_start.replace(day=last_day)

                if record.payment_date:
                    max_tva_date = record.payment_date + relativedelta(years=1)
                    if tva_start > max_tva_date:
                        raise ValidationError("Le Mois TVA ne peut pas être postérieur de plus d'un an à la date de paiement.")

                if record.invoice_date:
                    if record.invoice_date > tva_end:
                        raise ValidationError("La Date Facture doit être dans le Mois TVA ou avant celui-ci.")
