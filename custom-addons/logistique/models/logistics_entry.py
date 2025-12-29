from odoo import models, fields, api

class LogisticsEntry(models.Model):
    _name = 'logistique.entry'
    _description = 'Entrée Logistique'
    _rec_name = 'dossier_id'

    # Core reference - Dossier is now the main entity
    dossier_id = fields.Many2one('logistique.dossier', string='Dossier / BL', required=True, ondelete='cascade')
    
    # Automatic display of dossier-related data (read-only)
    container_ids = fields.One2many(related='dossier_id.container_ids', string='Conteneurs', readonly=True)
    cheque_ids = fields.One2many(related='dossier_id.cheque_ids', string='Chèques', readonly=True)
    
    # Finance numbers (from dossier, readonly for logistics)
    prov_number = fields.Char(related='dossier_id.prov_number', string='N° Prov', readonly=True, store=False)
    def_number = fields.Char(related='dossier_id.def_number', string='N° Def', readonly=True, store=False)
    
    # Optional container reference (for backward compatibility or specific tracking)
    container_id = fields.Many2one('logistique.container', string='Container (Optionnel)', domain="[('dossier_id', '=', dossier_id)]")

    
    # Week and status
    week = fields.Char(string='Semaine')
    status = fields.Selection([
        ('in_progress', 'En cours'),
        ('get_out', 'Get Out'),
        ('closed', 'Cloturé'),
    ], string='Status', default='in_progress')
    
    # Company and supplier info
    ste_id = fields.Many2one('logistique.ste', string='Société')
    supplier_id = fields.Many2one('logistique.supplier', string='Supplier')
    invoice_number = fields.Char(string='Invoice Number')
    
    # Product details
    article_id = fields.Many2one('logistique.article', string='Article')
    details = fields.Char(string='Details')
    weight = fields.Float(string='Poids')
    
    # Financial details
    price_unit = fields.Float(string='P.U', digits=(16, 4))
    amount_total = fields.Float(string='Total', compute='_compute_amount_total', store=True)
    
    # Audit
    saisi_par = fields.Char(string='Saisi par')
    
    @api.depends('price_unit', 'weight')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.price_unit * rec.weight
    
    # Logistics info
    incoterm = fields.Selection([
        ('cfr', 'CFR'),
        ('fob', 'FOB'),
    ], string='Incoterm')
    free_time = fields.Integer(string='Free Time')
    shipping_id = fields.Many2one('logistique.shipping', string='Shipping Company')
    eta = fields.Date(string='ETA')
    doc_status = fields.Char(string='Document Status')
    remarks = fields.Char(string='Remarks')
    
    # BL number from dossier
    bl_number = fields.Char(string='BL Number', related='dossier_id.name', store=True, readonly=True)

    @api.model
    def create(self, vals):
        # Create the logistics entry
        record = super(LogisticsEntry, self).create(vals)
        
        # Automatically create corresponding finance tracking record
        self.env['finance.logistics.tracking'].sudo().create({
            'dossier_id': record.dossier_id.id,
        })
        
        return record

