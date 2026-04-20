from odoo import models, fields, api

class FinanceChequePhysical(models.Model):
    _name = 'finance.cheque.physical'
    _description = 'Chèque Physique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name_custom'

    active = fields.Boolean(string='Actif', default=True)
    name = fields.Char(string='N° Chèque', required=True, index=True, tracking=True)
    ste_id = fields.Many2one('finance.ste', string='Société', required=True, tracking=True)
    
    datacheque_ids = fields.One2many('datacheque', 'physical_cheque_id', string='Répartitions (Datacheque)')
    
    amount_total = fields.Float(string='Montant Total', compute='_compute_amount_total', store=True, tracking=True)
    
    # Computed fields from the first linked datacheque (source of truth for shared data)
    date_emission = fields.Date(string="Date d'émission", compute='_compute_shared_info', store=True)
    date_echeance = fields.Date(string="Date d'échéance", compute='_compute_shared_info', store=True)
    date_encaissement = fields.Date(string="Date d'encaissement", compute='_compute_shared_info', store=True)
    benif_id = fields.Many2one('finance.benif', string='Bénéficiaire', compute='_compute_shared_info', store=True)
    
    credit = fields.Float(string="Crédit", compute='_compute_credit_debit')
    debit = fields.Float(string="Encaissement", compute='_compute_credit_debit')
    
    display_name_custom = fields.Char(string="Nom complet", compute='_compute_display_name_custom', store=True)
    
    encours = fields.Selection([
        ('encaisse', 'Encaissé'),
        ('non_encaisse', 'Non encaissé'),
    ], string='Status Encaissement', compute='_compute_encours', store=True)

    _sql_constraints = [
        ('unique_chq_ste', 'unique(name, ste_id)', 'Ce chèque physique existe déjà pour cette société.')
    ]

    @api.depends('name', 'ste_id', 'amount_total')
    def _compute_display_name_custom(self):
        for rec in self:
            amount_str = "{:,.2f}".format(rec.amount_total).replace(',', ' ')
            rec.display_name_custom = f"CHQ {rec.name} - {rec.ste_id.name} ({amount_str} MAD)"

    @api.depends('datacheque_ids.amount')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.datacheque_ids.mapped('amount'))

    @api.depends('datacheque_ids', 'datacheque_ids.date_emission', 'datacheque_ids.date_echeance', 'datacheque_ids.benif_id', 'datacheque_ids.date_encaissement')
    def _compute_shared_info(self):
        for rec in self:
            if rec.datacheque_ids:
                # Take info from the first one found (assuming they should be consistent for the same physical cheque)
                first = rec.datacheque_ids[0]
                rec.date_emission = first.date_emission
                rec.date_echeance = first.date_echeance
                rec.benif_id = first.benif_id
                rec.date_encaissement = first.date_encaissement
            else:
                rec.date_emission = False
                rec.date_echeance = False
                rec.benif_id = False
                rec.date_encaissement = False

    @api.depends('amount_total', 'datacheque_ids.amount', 'datacheque_ids.encours', 'datacheque_ids.date_encaissement')
    def _compute_credit_debit(self):
        for rec in self:
            rec.credit = rec.amount_total or 0.0
            total_debit = 0.0
            if rec.datacheque_ids:
                for split in rec.datacheque_ids:
                    if split.date_encaissement:
                        total_debit += split.amount
            rec.debit = total_debit

    @api.depends('datacheque_ids.encours')
    def _compute_encours(self):
        for rec in self:
            # If ANY of the splits is 'encaisse', we consider the physical cheque as encaisse?
            # Or ALL? Usually, a physical cheque is cashed once.
            # If it's split, all splits should share the same status technically.
            # We take the status of the first one found that is encaisse, or default to non_encaisse
            
            # Logic: If any datacheque has date_encaissement, then physical is 'encaisse'
            if any(d.date_encaissement for d in rec.datacheque_ids):
                rec.encours = 'encaisse'
            else:
                rec.encours = 'non_encaisse'
