from odoo import models, fields, api

class SutraConfigSte(models.Model):
    _name = 'sutra.config.ste'
    _description = 'Configuration SUTRA par Societe'

    ste_id = fields.Many2one('logistique.ste', string='Societe', required=True)
    amount_single = fields.Float(string='Montant (1 Conteneur)', required=True)
    amount_multiple = fields.Float(string='Montant (Plusieurs)', required=True)

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
    amount = fields.Float(string='Montant SUTRA', tracking=True)
    facture_ids = fields.One2many('sutra.facture', 'sutra_id', string='Factures')

    dum = fields.Char(string='DUM', compute='_compute_dum', store=True)
    payment_state = fields.Selection([
        ('non_paye', 'Non Paye'),
        ('paye', 'Paye')
    ], string='Etat de Paiement', compute='_compute_payment_state', store=True)

    @api.depends('logistics_id', 'logistics_id.dum', 'logistics_id.tanger_med_dum')
    def _compute_dum(self):
        for rec in self:
            rec.dum = rec.logistics_id.tanger_med_dum or rec.logistics_id.dum or ''

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
                    if not vals.get('amount') and log_entry.ste_id:
                        config = self.env['sutra.config.ste'].search([('ste_id', '=', log_entry.ste_id.id)], limit=1)
                        if config:
                            if log_entry.container_count and log_entry.container_count > 1:
                                vals['amount'] = config.amount_multiple
                            else:
                                vals['amount'] = config.amount_single
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
