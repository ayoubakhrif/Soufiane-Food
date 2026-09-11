from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class SutraConfigSte(models.Model):
    _name = 'sutra.config.ste'
    _description = 'Configuration SUTRA par Societe'

    ste_id = fields.Many2one('logistique.ste', string='Societe', required=True)
    amount_single = fields.Float(string='Montant (1 Conteneur)', required=True)
    amount_multiple = fields.Float(string='Montant (Plusieurs)', required=True)
    amount_temsa = fields.Float(string='Montant TEMSA')

    amount_unbilled = fields.Float(string='Dettes Engagees (Non facturees)', compute='_compute_sutra_debts')
    amount_unpaid = fields.Float(string='Dettes Reelles (A Payer)', compute='_compute_sutra_debts')
    amount_total_debt = fields.Float(string='Dette Totale SUTRA', compute='_compute_sutra_debts')

    def _compute_sutra_debts(self):
        for rec in self:
            if not rec.ste_id:
                rec.amount_unbilled = 0.0
                rec.amount_unpaid = 0.0
                rec.amount_total_debt = 0.0
                continue
            
            dossiers = self.env['sutra.dossier'].search([('logistics_id.ste_id', '=', rec.ste_id.id)])
            unbilled_amount = sum(d.amount for d in dossiers if not d.facture_ids)
            
            unpaid_invoices = self.env['sutra.facture'].search([
                ('sutra_id', 'in', dossiers.ids),
                ('state', 'in', ['non_paye', 'encours'])
            ])
            unpaid_amount = sum(unpaid_invoices.mapped('amount'))
            
            rec.amount_unbilled = unbilled_amount
            rec.amount_unpaid = unpaid_amount
            rec.amount_total_debt = unbilled_amount + unpaid_amount

    _sql_constraints = [
        ('ste_unique', 'unique(ste_id)', 'Une configuration existe deja pour cette societe !')
    ]

class SutraDossier(models.Model):
    _name = 'sutra.dossier'
    _description = 'Dossier de Transit SUTRA'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nom', required=True, tracking=True)
    logistics_id = fields.Many2one('logistique.entry', string='Dossier Logistique', tracking=True)
    amount = fields.Float(string='Montant SUTRA', compute='_compute_sutra_amount', store=True, readonly=False, tracking=True)

    @api.depends('logistics_id.container_count', 'logistics_id.passed_control_type', 'logistics_id.ste_id')
    def _compute_sutra_amount(self):
        for rec in self:
            if rec.logistics_id and rec.logistics_id.ste_id:
                config = self.env['sutra.config.ste'].search([('ste_id', '=', rec.logistics_id.ste_id.id)], limit=1)
                if config:
                    amt = config.amount_multiple if getattr(rec.logistics_id, 'container_count', 0) > 1 else config.amount_single
                    if getattr(rec.logistics_id, 'passed_control_type', 'none') in ('visite', 'analyse', 'both'):
                        amt += config.amount_temsa
                    rec.amount = amt
    facture_ids = fields.One2many('sutra.facture', 'sutra_id', string='Factures')

    dum = fields.Char(string='DUM', compute='_compute_dum', store=True)
    payment_state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('paye', 'Paye')
    ], string='Etat de Paiement', compute='_compute_payment_state', store=True)

    @api.depends('logistics_id', 'logistics_id.tanger_med_dum')
    def _compute_dum(self):
        for rec in self:
            douane_dum = getattr(rec.logistics_id, 'dum', False)
            rec.dum = rec.logistics_id.tanger_med_dum or douane_dum or ''

    @api.depends('facture_ids', 'facture_ids.state')
    def _compute_payment_state(self):
        for rec in self:
            if not rec.facture_ids:
                rec.payment_state = 'non_paye'
            elif all(f.state == 'paye' for f in rec.facture_ids):
                rec.payment_state = 'paye'
            else:
                rec.payment_state = 'non_paye'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('logistics_id'):
                log_entry = self.env['logistique.entry'].browse(vals['logistics_id'])
                if log_entry.exists():
                    if not vals.get('name'):
                        vals['name'] = f'SUTRA - {log_entry.display_name}'
                    # Amount is now handled by the compute method _compute_sutra_amount
        return super(SutraDossier, self).create(vals_list)

class SutraFacture(models.Model):
    _name = 'sutra.facture'
    _description = 'Facture SUTRA'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sutra_id = fields.Many2one('sutra.dossier', string='Dossier SUTRA', ondelete='cascade', required=True)
    name = fields.Char(string='Numero de Facture', required=True, tracking=True)
    date = fields.Date(string='Date', tracking=True)
    amount = fields.Float(string='Montant TTC', tracking=True)
    state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('encours', 'En Cours'),
        ('paye', 'Paye')
    ], string='Statut Paiement', default='non_paye', tracking=True)
    
    cheque_id = fields.Many2one('finance2.cheque', string='Cheque de Paiement', tracking=True)
    pdf_file = fields.Binary(string='Facture (PDF)', attachment=True)
    pdf_filename = fields.Char(string='Nom du fichier PDF')

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if rec.name:
                duplicates = self.search([('name', '=', rec.name), ('id', '!=', rec.id)])
                if duplicates:
                    raise ValidationError(f"La facture SUTRA '{rec.name}' a déjà été saisie dans le système !")

    @api.constrains('sutra_id', 'amount')
    def _check_unique_dossier_amount(self):
        for rec in self:
            if rec.sutra_id and rec.amount:
                duplicates = self.search([
                    ('sutra_id', '=', rec.sutra_id.id),
                    ('amount', '=', rec.amount),
                    ('id', '!=', rec.id)
                ])
                if duplicates:
                    raise ValidationError(f"Une facture avec le même montant ({rec.amount} DH) existe déjà pour le dossier {rec.sutra_id.name} (DUM: {rec.sutra_id.dum or 'N/A'}) !")


    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if rec.name:
                domain = [('name', '=', rec.name), ('id', '!=', rec.id)]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(f"La facture SUTRA '{rec.name}' a déjà été saisie (numéro de facture en double) !")

    @api.constrains('sutra_id')
    def _check_unique_dossier(self):
        for rec in self:
            if rec.sutra_id:
                domain = [('sutra_id', '=', rec.sutra_id.id), ('id', '!=', rec.id)]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(f"Le dossier SUTRA '{rec.sutra_id.dum or rec.sutra_id.name}' a déjà une facture SUTRA liée. Impossible d'en lier une deuxième !")

