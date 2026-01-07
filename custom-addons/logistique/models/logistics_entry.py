import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LogisticsEntry(models.Model):
    _name = 'logistique.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entrée Logistique'
    _rec_name = 'dossier_id'

    # Core reference - Dossier is now the main entity
    dossier_id = fields.Many2one('logistique.dossier', string='Dossier / BL', required=False, ondelete='cascade')
    
    # Automatic display of dossier-related data (read-only)
    container_ids = fields.One2many('logistique.container', 'entry_id', string='Conteneurs')
    cheque_ids = fields.One2many(related='dossier_id.cheque_ids', string='Chèques', readonly=False)
    
    # Finance numbers (from dossier, readonly for logistics)
    prov_number = fields.Char(related='dossier_id.prov_number', string='N° Prov', readonly=True, store=False)
    def_number = fields.Char(related='dossier_id.def_number', string='N° Def', readonly=True, store=False)
    
    # Optional container reference (for backward compatibility or specific tracking)
    container_id = fields.Many2one('logistique.container', string='Container (Optionnel)', domain="[('dossier_id', '=', dossier_id)]")

    
    # Week and status
    week = fields.Char(
        string="Semaine",
        help="Format : W01 à W52 (ex: W12)",
        store=True
    )
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
        ('emirate', 'EMIRATE'),
        ('exw', 'EXW'),
    ], string='Incoterm')
    free_time = fields.Integer(string='Free Time')
    shipping_id = fields.Many2one('logistique.shipping', string='Company')
    eta = fields.Date(string='ETA')

    doc_status = fields.Char(string='Document Status')
    remarks = fields.Char(string='Remarks')
    
    # Purchase Specific Fields (Hidden in Logistics View)
    purchase_state = fields.Selection([
        ('initial', 'Initial'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Purchase Purchase', default='initial', required=True, tracking=True)

    contract_num = fields.Char(string='Contract Number') # Keep for legacy/manual if needed? Or replace with related?
    # contract_id moved to achat module to avoid dependency cycle
    # free_time_negotiated moved to achat module

    # Documents
    doc_invoice = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Commercial Invoice', default='absent')
    doc_packing = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Packing List', default='absent')
    doc_bl = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Bill of Lading', default='absent')
    doc_quality = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Quality Certificate', default='absent')
    doc_origin = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Certificate of Origin', default='absent')

    lot = fields.Char(string='Lot')
    dhl_number = fields.Char(string='DHL Number')
    eta_dhl = fields.Date(string='ETA DHL')
    origin = fields.Char(string='Origin')
    
    def action_move_to_draft(self):
        self.write({'purchase_state': 'draft'})

    def action_confirm_purchase(self):
        self.write({'purchase_state': 'confirmed'})

    # _onchange_contract_id moved to achat module
    
    # BL number from dossier
    bl_number = fields.Char(string='BL Number', store=True)
    container_count = fields.Integer(
        string="Nb Conteneurs",
        related="dossier_id.container_count",
        readonly=True,
        store=False
    )

    cheque_count = fields.Integer(
        string="Nb Chèques",
        related="dossier_id.cheque_count",
        readonly=True,
        store=False
    )


    # Computed field to expose standard attachments in a form view field
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        string='Documents',
        compute='_compute_attachment_ids',
        inverse='_inverse_attachment_ids',
        help='Dedicated documents upload area'
    )

    def _compute_attachment_ids(self):
        for rec in self:
            rec.attachment_ids = self.env['ir.attachment'].search([
                ('res_model', '=', 'logistique.entry'),
                ('res_id', '=', rec.id)
            ])

    def _inverse_attachment_ids(self):
        for rec in self:
            for attachment in rec.attachment_ids:
                attachment.write({'res_model': 'logistique.entry', 'res_id': rec.id})

    @api.model
    def create(self, vals):
        # Create dossier if bl_number is present and dossier_id is missing
        if vals.get('bl_number') and not vals.get('dossier_id'):
            # Check if dossier exists first to avoid unique constraint error
            existing_dossier = self.env['logistique.dossier'].search([
                ('name', '=', vals.get('bl_number'))
            ], limit=1)
            
            if existing_dossier:
                vals['dossier_id'] = existing_dossier.id
            else:
                dossier = self.env['logistique.dossier'].create({
                    'name': vals.get('bl_number')
                })
                vals['dossier_id'] = dossier.id

        # Create the logistics entry
        record = super(LogisticsEntry, self).create(vals)
        
        # Sync containers with dossier
        if record.dossier_id and record.container_ids:
            record.container_ids.write({'dossier_id': record.dossier_id.id})

        # Automatically create corresponding finance tracking record
        self.env['finance.logistics.tracking'].sudo().create({
            'dossier_id': record.dossier_id.id,
        })
        
        return record

    def write(self, vals):
        res = super(LogisticsEntry, self).write(vals)
        for rec in self:
            # Sync BL Number to Dossier Name
            if 'bl_number' in vals and rec.dossier_id:
                rec.dossier_id.name = vals['bl_number']
            
            # Sync Containers to Dossier (if added/changed)
            if 'container_ids' in vals and rec.dossier_id:
                rec.container_ids.write({'dossier_id': rec.dossier_id.id})
                
        return res
    @api.constrains('week')
    def _check_week_format(self):
        for rec in self:
            if rec.week and not re.match(r'^W(0[1-9]|[1-4][0-9]|5[0-2])$', rec.week):
                raise ValidationError(
                    "Format de semaine invalide.\n"
                    "Utilisez : W01 à W52 (ex: W12)"
                )

    #@api.constrains('incoterm', 'free_time')
    #def _check_free_time_by_incoterm(self):
     #   for rec in self:
      #      if rec.incoterm in ('fob', 'cfr'):
       #         if not rec.free_time:
        #            raise ValidationError(
         #               "Free Time is required when Incoterm is FOB or CFR."
          #          )
           #     if rec.free_time < 7:
            #        raise ValidationError(
             #           "Free Time must be at least 14 days when Incoterm is FOB or CFR."
              #      )
