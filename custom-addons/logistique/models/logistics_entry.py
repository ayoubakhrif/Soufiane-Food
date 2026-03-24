import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import requests
import json
from datetime import datetime

_logger = logging.getLogger(__name__)

TERMINAL49_API_TOKEN = 'dD7a1vYR4KGS9iXE463Mv2dN'
TERMINAL49_BASE_URL = 'https://api.terminal49.com/v2'

class LogisticsEntry(models.Model):
    _name = 'logistique.entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entrée Logistique'
    _rec_name = 'bl_number'

    # Core reference - Dossier is now the main entity
    dossier_id = fields.Many2one('logistique.dossier', string='Dossier / BL', required=False, ondelete='cascade')
    
    # Automatic display of dossier-related data (read-only)
    container_ids = fields.One2many('logistique.container', 'entry_id', string='Conteneurs')
    cheque_ids = fields.One2many(related='dossier_id.cheque_ids', string='Chèques', readonly=False, tracking=True)
    
    # Finance numbers (from dossier, readonly for logistics)
    prov_number = fields.Char(related='dossier_id.prov_number', string='N° Prov', readonly=True, store=False)
    def_number = fields.Char(related='dossier_id.def_number', string='N° Def', readonly=True, store=False)
    
    # Optional container reference (for backward compatibility or specific tracking)
    container_id = fields.Many2one('logistique.container', string='Container (Optionnel)', domain="[('dossier_id', '=', dossier_id)]")

    container_names = fields.Char(
        string="Conteneurs",
        compute="_compute_container_names",
        store=True,
    )

    @api.depends('container_ids.name')
    def _compute_container_names(self):
        for rec in self:
            rec.container_names = ', '.join(
                rec.container_ids.mapped('name')
            )

    
    # Week and status
    week = fields.Char(
        string="Semaine",
        help="Format : W01 à W52 (ex: W12)",
        store=True
    )
    status = fields.Selection([
        ('in_progress', 'En cours'),
        ('get_out', 'Gate Out'),
        ('closed', 'Clotured'),
    ], string='Status', default='in_progress', tracking=True)
    
    # Company and supplier info
    ste_id = fields.Many2one('logistique.ste', string='Société')
    supplier_id = fields.Many2one('logistique.supplier', string='Supplier')
    invoice_number = fields.Char(string='Invoice Number')
    charge_transport_local = fields.Float(string='Charge de transport local')
    
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
    shipping_id = fields.Many2one('logistique.shipping', string='Company', tracking=True)
    eta = fields.Date(string='ETA', tracking=True)

    doc_status = fields.Char(string='Document Status')
    remarks = fields.Char(string='Remarks')
    
    # Purchase Specific Fields (Hidden in Logistics View)
    purchase_state = fields.Selection([
        ('initial', 'Initial'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Purchase state', default='initial', required=True, tracking=True)

    contract_num = fields.Char(string='Contract Number') # Keep for legacy/manual if needed? Or replace with related?
    # contract_id moved to achat module to avoid dependency cycle
    # free_time_negotiated moved to achat module

    # Documents
    doc_invoice = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Commercial Invoice', default='absent')
    doc_packing = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Packing List', default='absent')
    doc_bl = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Bill of Lading', default='absent')
    doc_fito = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Fito sanitaire', default='absent')
    doc_origin = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Certificate of Origin', default='absent')
    doc_health = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Health Certificate', default='absent')
    doc_fumigation = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('confirmed', 'Confirmed')], string='Fumigation Certificate', default='absent')


    lot = fields.Char(string='Lot')
    dhl_number = fields.Char(string='DHL Number')
    eta_dhl = fields.Date(string='ETA DHL')
    entry_date = fields.Date(string='Date of entry', tracking=True)
    exit_date = fields.Date(string='Date of exit', tracking=True)
    bad_date = fields.Date(string='Date of BAD', tracking=True)
    
    # Terminal49 Integration Fields
    terminal49_shipment_id = fields.Char(string='ID Shipment Terminal49', copy=False, tracking=True)
    last_terminal49_sync = fields.Datetime(string='Last T49 Sync', copy=False)

    def _terminal49_get_tracking_number(self):
        """Returns the BL number or the first container number."""
        self.ensure_one()
        if self.bl_number:
            return str(self.bl_number)
        if self.container_ids and self.container_ids[0].name:
            return str(self.container_ids[0].name)
        return ""

    def action_terminal49_register(self):
        """Manually register the shipment in Terminal49."""
        for rec in self:
            rec._terminal49_register_shipment()

    def _terminal49_register_shipment(self):
        """Sends a POST request to register tracking in Terminal49."""
        self.ensure_one()
        tracking_number = self._terminal49_get_tracking_number()
        if not tracking_number or self.terminal49_shipment_id:
            return

        headers = {
            'Authorization': f'Token {TERMINAL49_API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # We try to track by BOL if possible, or container
        # Extraction du SCAC (4 premières lettres) et du numéro (le reste)
        scac = tracking_number[:4].upper()
        number_only = tracking_number[4:]

        payload = {
            "data": {
                "type": "tracking_request",
                "attributes": {
                    "request_number": number_only, # Changé 'number' en 'request_number'
                    "scac": scac
                }
            }
        }

        try:
            response = requests.post(f"{TERMINAL49_BASE_URL}/tracking_requests", headers=headers, json=payload, timeout=10)
            if response.status_code in (200, 201):
                data = response.json()
                shipment_id = data.get('data', {}).get('relationships', {}).get('shipment', {}).get('data', {}).get('id')
                if shipment_id:
                    self.write({'terminal49_shipment_id': shipment_id})
                    self.message_post(body=_("Dossier enregistré sur Terminal49 (ID: %s)") % shipment_id)
            elif response.status_code == 422:
                # Already exists or invalid
                _logger.warning("Terminal49: Error 422 for %s - %s", tracking_number, response.text)
            else:
                _logger.error("Terminal49 Register Error: %s - %s", response.status_code, response.text)
        except Exception as e:
            _logger.exception("Terminal49 Registration Exception: %s", str(e))

    def action_terminal49_update_eta(self):
        """Force update ETA from Terminal49."""
        for rec in self:
            rec._terminal49_update_eta()

    def _terminal49_update_eta(self):
        """Retrieves latest shipment data and updates ETA."""
        self.ensure_one()
        if not self.terminal49_shipment_id:
            # Try registering if not done
            self._terminal49_register_shipment()
            if not self.terminal49_shipment_id:
                return

        headers = {
            'Authorization': f'Token {TERMINAL49_API_TOKEN}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.get(f"{TERMINAL49_BASE_URL}/shipments/{self.terminal49_shipment_id}", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                attrs = data.get('data', {}).get('attributes', {})
                
                # Priority: pod_eta_at (Port of Discharge ETA) -> predicted_eta
                new_eta_str = attrs.get('pod_eta_at') or attrs.get('predicted_eta')
                
                if new_eta_str:
                    # Date format from T49 usually ISO YYYY-MM-DD...
                    new_eta_date = new_eta_str.split('T')[0]
                    if str(self.eta) != new_eta_date:
                        old_eta = self.eta
                        self.write({
                            'eta': new_eta_date,
                            'last_terminal49_sync': fields.Datetime.now()
                        })
                        self.message_post(body=_(
                            "Mise à jour automatique Terminal49 : ETA modifié de %s à %s"
                        ) % (old_eta or 'vide', new_eta_date))
                    else:
                        self.write({'last_terminal49_sync': fields.Datetime.now()})
            else:
                _logger.error("Terminal49 Update Error: %s - %s", response.status_code, response.text)
        except Exception as e:
            _logger.exception("Terminal49 Update Exception: %s", str(e))

    @api.model
    def cron_terminal49_sync_eta(self):
        """Cron method to sync ETA for all active entries."""
        entries = self.search([
            ('port_status', '=', 'on_port'),
            ('terminal49_shipment_id', '!=', False)
        ])
        _logger.info("Terminal49 Sync: Processing %s entries", len(entries))
        for entry in entries:
            entry._terminal49_update_eta()
            self.env.cr.commit() # Commit each to avoid losing progress if one fails? 
            # Or depend on individual try/except in _terminal49_update_eta
    
    port_status = fields.Selection([
        ('on_port', 'On Port'),
        ('exited', 'Exited'),
    ], string='Port Status', default='on_port', tracking=True)

    exit_comment = fields.Text(string='Commentaire Sortie', tracking=True)

    def action_exit_port(self):
        self.write({
            'port_status': 'exited',
            'exit_date': fields.Date.context_today(self)
        })
    consolidator_id = fields.Many2one('logistique.consolidator', string='FFW')
    surestarie_amount = fields.Float(
        string="Surestarie",
        related="dossier_id.surestarie_amount",
        readonly=True,
        store=True
    )
    comment = fields.Char(string='Comments')
    fret = fields.Float(
        string='Fret',
        related='dossier_id.fret_amount',
        store=True,
        readonly=True
    )
    thc_amount = fields.Float(
        string="THC",
        related="dossier_id.thc_amount",
        readonly=True,
        store=True
    )

    magasinage_amount = fields.Float(
        string="Magasinage",
        related="dossier_id.magasinage_amount",
        readonly=True,
        store=True
    )

    def action_move_to_draft(self):
        self.write({'purchase_state': 'draft'})

    def action_set_gate_out(self):
        for rec in self:
            if not rec.bad_date and rec.incoterm != 'emirate':
                raise ValidationError(_("La date BAD est requise pour passer à l'étape Gate Out."))
            if rec.incoterm == 'fob' and rec.fret <= 0:
                raise ValidationError(_("Le montant du Fret doit être supérieur à 0 quand l'Incoterm est FOB."))
            rec.write({'status': 'get_out'})

    def action_set_closed(self):
        for rec in self:
            if not rec.entry_date and rec.incoterm != 'emirate':
                raise ValidationError(_("La date d'entrée est requise pour clôturer."))
            if not rec.exit_date and rec.incoterm != 'emirate':
                raise ValidationError(_("La date de sortie est requise pour clôturer."))
            


            rec.write({'status': 'closed'})

    # _onchange_contract_id moved to achat module
    
    # BL number from dossier
    bl_number = fields.Char(related='dossier_id.name', string='BL Number', store=True, readonly=False)
    container_count = fields.Integer(
        string="Nb Conteneurs",
        compute="_compute_container_count",
        readonly=True,
        store=True
    )

    @api.depends('container_ids')
    def _compute_container_count(self):
        for rec in self:
            rec.container_count = len(rec.container_ids)


    cheque_count = fields.Integer(
        string="Nb Chèques",
        related="dossier_id.cheque_count",
        readonly=True,
        store=False
    )
    deduction_ids = fields.One2many(
        'logistique.dossier.deduction',
        'entry_id',
        string='Déductions',
        tracking=True
    )
    transfer_ids = fields.One2many(
        'logistique.dossier.transfer',
        'entry_id',
        string='Virements',
        tracking=True
    )
    logistique_doc_ids = fields.One2many(
        'logistique.doc',
        'entry_id',
        string='Documents (Drive)',
    )


    @api.onchange('contract_id')
    def _onchange_contract_id_origin(self):
        if self.contract_id:
            self.origin_id = self.contract_id.origin_id

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
            
            # Since bl_number is now related, we don't want Odoo to try writing it twice during creation
            vals.pop('bl_number', None)

        # Create the logistics entry
        record = super().create(vals)
        
        # Register in Terminal49
        record._terminal49_register_shipment()
        
        # Sync containers with dossier
        if record.dossier_id and record.container_ids:
            record.container_ids.write({'dossier_id': record.dossier_id.id})

        # Automatically create corresponding finance tracking record
        existing_tracking = self.env['finance.logistics.tracking'].sudo().search([
            ('dossier_id', '=', record.dossier_id.id)
        ], limit=1)
        
        if not existing_tracking:
            self.env['finance.logistics.tracking'].sudo().create({
                'dossier_id': record.dossier_id.id,
            })
        
        return record

    def write(self, vals):
        # If status is being changed, set saisi_par to current user's name
        if 'status' in vals:
            vals['saisi_par'] = self.env.user.name
        
        res = super().write(vals)
        for rec in self:
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

    @api.constrains('incoterm', 'free_time')
    def _check_free_time_by_incoterm(self):
        for rec in self:
            if rec.incoterm in ('fob', 'cfr'):
                if not rec.free_time:
                    raise ValidationError(
                        "Free Time is required when Incoterm is FOB or CFR."
                    )
                #if rec.free_time < 14:
                #    raise ValidationError(
                #        "Free Time must be at least 14 days when Incoterm is FOB or CFR."
                #    )
