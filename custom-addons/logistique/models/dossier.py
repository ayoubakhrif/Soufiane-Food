from odoo import models, fields, api

class LogistiqueDossier(models.Model):
    _name = 'logistique.dossier'
    _description = 'Dossier Logistique'
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Le numéro de BL doit être unique !"),
    ]

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
    
    # One2many relationships
    container_ids = fields.One2many('logistique.container', 'dossier_id', string='Conteneurs')
    cheque_ids = fields.One2many('logistique.dossier.cheque', 'dossier_id', string='Chèques')
    entry_ids = fields.One2many('logistique.entry', 'dossier_id', string='Entrées Logistiques')
    deduction_ids = fields.One2many(
        'logistique.dossier.deduction',
        'dossier_id',
        string='Déductions'
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

    @api.depends('container_ids', 'cheque_ids')
    def _compute_counts(self):
        for dossier in self:
            dossier.container_count = len(dossier.container_ids)
            dossier.cheque_count = len(dossier.cheque_ids)

    @api.depends(
        'cheque_ids.amount',
        'cheque_ids.type',
        'deduction_ids.amount',
        'deduction_ids.type',
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

            # --- Totaux finaux ---
            rec.surestarie_amount = surestarie_cheques + surestarie_deductions
            rec.thc_amount = thc_cheques + thc_deductions
            rec.magasinage_amount = magasinage_cheques + magasinage_deductions
