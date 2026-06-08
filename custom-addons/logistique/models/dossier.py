from odoo import models, fields, api

class LogistiqueDossier(models.Model):
    _name = 'logistique.dossier'
    _description = 'Dossier Logistique'

    name = fields.Char(string='Numéro BL', required=True)
    
    # Finance-managed fields
    prov_number = fields.Char(string='N° Prov', help="Numéro provisoire géré par Finance")
    def_number = fields.Char(string='N° Def', help="Numéro définitif géré par Finance")
    
    # Common Info (Lifted from Entries)
    ste_id = fields.Many2one('logistique.ste', string='Société')
    supplier_id = fields.Many2one('logistique.supplier', string='Fournisseur')
    eta = fields.Date(string='ETA')

    # DHL Info
    dhl_number = fields.Char(string='Numéro DHL')
    eta_dhl = fields.Date(string='ETA DHL')

    container_names = fields.Char(
        string="Conteneurs",
        compute="_compute_container_names",
        store=True,
    )

    @api.depends('entry_ids.container_ids.name')
    def _compute_container_names(self):
        for rec in self:
            containers = rec.entry_ids.mapped('container_ids')
            rec.container_names = ', '.join(containers.mapped('name'))
    
    # DUM Info (Refactored to douane module)
    # dum = fields.Char...
    # dum_ids = fields.Char...
    
    # One2many relationships
    cheque_ids = fields.One2many('logistique.dossier.cheque', 'dossier_id', string='Chèques')
    entry_ids = fields.One2many('logistique.entry', 'dossier_id', string='Entrées Logistiques')
    deduction_ids = fields.One2many(
        'logistique.dossier.deduction',
        'dossier_id',
        string='Déductions'
    )
    transfer_ids = fields.One2many(
        'logistique.dossier.transfer',
        'dossier_id',
        string='Virements'
    )
    sutra_ids = fields.One2many(
        'logistique.dossier.sutra',
        'dossier_id',
        string='Sutra'
    )
    container_count = fields.Integer(
        string="Nb Conteneurs",
        compute="_compute_counts",
        store=True
    )

    cheque_count = fields.Integer(
        string="Nb Chèques",
        compute="_compute_counts",
        store=True
    )

    surestarie_amount = fields.Float(
        string="Surestarie",
        compute="_compute_charges",
        store=True
    )
    thc_amount = fields.Float(
        string="THC",
        compute="_compute_charges",
        store=True
    )
    magasinage_amount = fields.Float(
        string="Magasinage",
        compute="_compute_charges",
        store=True
    )
    fret_amount = fields.Float(
        string="Fret",
        compute="_compute_charges",
        store=True
    )
    assurance_amount = fields.Float(
        string="Assurance",
        compute="_compute_charges",
        store=True
    )

    @api.depends('entry_ids.container_ids', 'cheque_ids')
    def _compute_counts(self):
        for dossier in self:
            all_containers = dossier.entry_ids.mapped('container_ids')
            dossier.container_count = len(all_containers)
            dossier.cheque_count = len(dossier.cheque_ids)

    @api.depends(
        'cheque_ids.amount',
        'cheque_ids.type',
        'deduction_ids.amount',
        'deduction_ids.type',
        'transfer_ids.amount',
        'transfer_ids.type',
        'sutra_ids.amount',
        'sutra_ids.type',
    )
    def _compute_charges(self):
        for rec in self:
            # --- Chèques ---
            surestarie_cheques = sum(
                c.amount for c in rec.cheque_ids if c.type == 'surestarie'
            )
            thc_cheques = sum(
                c.amount for c in rec.cheque_ids if c.type == 'thc'
            )
            magasinage_cheques = sum(
                c.amount for c in rec.cheque_ids if c.type == 'magasinage'
            )

            surestarie_deductions = sum(
                d.amount for d in rec.deduction_ids if d.type == 'surestarie'
            )
            thc_deductions = sum(
                d.amount for d in rec.deduction_ids if d.type == 'thc'
            )
            magasinage_deductions = sum(
                d.amount for d in rec.deduction_ids if d.type == 'magasinage'
            )

            # --- Virements ---
            surestarie_transfers = sum(
                t.amount for t in rec.transfer_ids if t.type == 'surestarie'
            )
            thc_transfers = sum(
                t.amount for t in rec.transfer_ids if t.type == 'thc'
            )
            magasinage_transfers = sum(
                t.amount for t in rec.transfer_ids if t.type == 'magasinage'
            )

            # --- Sutra ---
            surestarie_sutra = sum(
                s.amount for s in rec.sutra_ids if s.type == 'surestarie'
            )
            thc_sutra = sum(
                s.amount for s in rec.sutra_ids if s.type == 'thc'
            )
            magasinage_sutra = sum(
                s.amount for s in rec.sutra_ids if s.type == 'magasinage'
            )

            # --- Totaux finaux ---
            rec.surestarie_amount = surestarie_cheques + surestarie_deductions + surestarie_transfers + surestarie_sutra
            rec.thc_amount = thc_cheques + thc_deductions + thc_transfers + thc_sutra
            rec.magasinage_amount = magasinage_cheques + magasinage_deductions + magasinage_transfers + magasinage_sutra
            
            # --- FRET ---
            rec.fret_amount = (
                sum(c.amount for c in rec.cheque_ids if c.type == 'fret') +
                sum(d.amount for d in rec.deduction_ids if d.type == 'fret') +
                sum(t.amount for t in rec.transfer_ids if t.type == 'fret') +
                sum(s.amount for s in rec.sutra_ids if s.type == 'fret')
            )

            # --- Assurance ---
            rec.assurance_amount = (
                sum(c.amount for c in rec.cheque_ids if c.type == 'assurance') +
                sum(d.amount for d in rec.deduction_ids if d.type == 'assurance') +
                sum(t.amount for t in rec.transfer_ids if t.type == 'assurance') +
                sum(s.amount for s in rec.sutra_ids if s.type == 'assurance')
            )