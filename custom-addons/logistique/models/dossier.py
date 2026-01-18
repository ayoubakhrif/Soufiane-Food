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
    
    # DUM Info (NOUVEAU)
    dum = fields.Char(
        string='N° DUM',
        compute='_compute_dum',
        store=True,
        help="Numéro DUM principal du dossier (récupéré depuis les entries)"
    )
    
    dum_ids = fields.Char(
        string='Tous les DUMs',
        compute='_compute_dum_ids',
        help="Liste de tous les DUMs liés à ce dossier"
    )
    
    # One2many relationships
    container_ids = fields.One2many('logistique.container', 'dossier_id', string='Conteneurs')
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
        'transfer_ids.amount',
        'transfer_ids.type',
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

            # --- Totaux finaux ---
            rec.surestarie_amount = surestarie_cheques + surestarie_deductions + surestarie_transfers
            rec.thc_amount = thc_cheques + thc_deductions + thc_transfers
            rec.magasinage_amount = magasinage_cheques + magasinage_deductions + magasinage_transfers

    # ============================================================
    # NOUVELLES MÉTHODES POUR AFFICHER LE DUM
    # ============================================================
    
    @api.depends('entry_ids.dum')
    def _compute_dum(self):
        """Récupère le premier DUM trouvé dans les entries liées"""
        for record in self:
            entry_with_dum = record.entry_ids.filtered(lambda e: e.dum)
            if entry_with_dum:
                # Prendre le premier DUM (ou le plus récent si trié)
                record.dum = entry_with_dum[0].dum
            else:
                record.dum = False

    @api.depends('entry_ids.dum')
    def _compute_dum_ids(self):
        """Liste tous les DUMs liés au dossier (séparés par virgule)"""
        for record in self:
            dums = record.entry_ids.filtered(lambda e: e.dum).mapped('dum')
            record.dum_ids = ', '.join(dums) if dums else False

    def name_get(self):
        """
        Affiche le DUM en priorité, puis le BL
        Format: "DUM123456" ou "BL789" ou "Dossier #123"
        """
        result = []
        for record in self:
            # Priorité d'affichage: DUM > BL > ID
            if record.dum:
                name = record.dum
            elif record.name:
                name = record.name
            else:
                name = f"Dossier #{record.id}"
            
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        Permet de rechercher un dossier par DUM ou par BL
        Exemple: Rechercher "123" trouvera DUM123 ou BL123
        """
        args = args or []
        if name:
            # Recherche sur DUM, BL ou ID
            domain = [
                '|', '|',
                ('dum', operator, name),
                ('name', operator, name),
                ('id', '=', name if name.isdigit() else 0)
            ]
            return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return super()._name_search(name, args, operator, limit, name_get_uid)