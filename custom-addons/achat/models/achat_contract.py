from odoo import models, fields, api

class AchatContract(models.Model):
    _name = 'achat.contract'
    _description = 'Purchase Contract'
    _order = 'date desc, id desc'

    name = fields.Char(string='Contract Number', required=True, copy=False)
    date = fields.Date(string='Contract Date', required=True, default=fields.Date.context_today)
    
    # Parties
    supplier_id = fields.Many2one('logistique.supplier', string='Supplier', required=True)
    ste_id = fields.Many2one('logistique.ste', string='Company', required=True)
    
    # Agreement Details
    article_id = fields.Many2one('logistique.article', string='Article', required=True)
    incoterm = fields.Selection([
        ('cfr', 'CFR'),
        ('fob', 'FOB'),
        ('emirate', 'EMIRATE'),
    ], string='Incoterm', required=True)
    origin = fields.Char(string='Origin')
    details = fields.Char(string='Details')
    
    # Quantitative Terms
    quantity_negotiated = fields.Integer(string='Total Containers', required=True, default=1)
    weight_total = fields.Float(string='Total Weight')
    free_time_negotiated = fields.Integer(string='Negotiated Free Time')
    
    # State Management
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='open', compute='_compute_state', store=True, readonly=False)
    
    # Relations
    dossier_ids = fields.One2many('logistique.entry', 'contract_id', string='Dossiers')
    
    # Consumption Computations
    quantity_consumed = fields.Integer(string='Consumed Containers', compute='_compute_consumption', store=True)
    quantity_remaining = fields.Integer(string='Remaining Containers', compute='_compute_consumption', store=True)

    @api.depends('dossier_ids', 'dossier_ids.container_count', 'quantity_negotiated')
    def _compute_consumption(self):
        for rec in self:
            # Only count containers from dossiers that are NOT cancelled (if cancellation existed)
            # Currently assuming all linked dossiers are valid
            consumed = sum(d.container_count for d in rec.dossier_ids)
            rec.quantity_consumed = consumed
            rec.quantity_remaining = rec.quantity_negotiated - consumed

    @api.depends('quantity_remaining')
    def _compute_state(self):
        for rec in self:
            # Auto-close if fully consumed, but allow manual override if user re-opens
            if rec.quantity_remaining <= 0 and rec.state == 'open':
                rec.state = 'closed'
            # Note: We don't auto-open because user might manually close a contract early
