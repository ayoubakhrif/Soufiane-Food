from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LogistiqueDossierCheque(models.Model):
    _name = 'logistique.dossier.cheque'
    _description = 'Chèque Dossier Logistique'

    cheque_serie = fields.Char(string='Série Chèque', required=True, size=7)
    date = fields.Date(string='Date')
    beneficiary_id = fields.Many2one('logistique.shipping', string='Bénéficiaire')
    amount = fields.Float(string='Montant', required=True)
    ste_id = fields.Many2one(
        'logistique.ste',
        string='Société',
        store=True,
        default=lambda self: self._default_ste_id()
    )

    def _default_ste_id(self):
        if self.env.context.get('default_dossier_id'):
            dossier = self.env['logistique.dossier'].browse(self.env.context['default_dossier_id'])
            return dossier.ste_id.id
        return False
    
    @api.onchange('dossier_id')
    def _onchange_dossier_id(self):
        for rec in self:
            if rec.dossier_id and not rec.ste_id:
                rec.ste_id = rec.dossier_id.ste_id
    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('fret', 'FRET'),
        ('surestarie', 'Surestarie'),
        ('assurance', 'Assurance'),
        ('autres', 'Autres factures'),
    ], string='Type')
    entry_id = fields.Many2one(
        'logistique.entry',
        string='Entrée Logistique',
        required=False,
        ondelete='cascade'
    )
    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier',
        store=True,
        readonly=True
    )

    def write(self, vals):
        # Fallback for write: preserve ste_id
        if 'ste_id' in vals and not vals['ste_id']:
            # If trying to clear ste_id, check if we have a dossier
            for rec in self:
                if rec.dossier_id and rec.dossier_id.ste_id:
                    # Force keep existing or reset from dossier
                    vals['ste_id'] = rec.dossier_id.ste_id.id
                    
        return super().write(vals)




    @api.model
    def create(self, vals):
        # Fallback: if ste_id is missing or False, try to get it from dossier
        dossier_id = vals.get('dossier_id') or self.env.context.get('default_dossier_id')
        
        if not vals.get('ste_id') and dossier_id:
            dossier = self.env['logistique.dossier'].browse(dossier_id)
            if dossier.ste_id:
                vals['ste_id'] = dossier.ste_id.id
                
        return super().create(vals)
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        entry_id = self.env.context.get('default_entry_id')
        if entry_id:
            entry = self.env['logistique.entry'].browse(entry_id)
            res.update({
                'ste_id': entry.ste_id.id if entry.ste_id else False,
                'dossier_id': entry.dossier_id.id if entry.dossier_id else False,
            })
        return res

    def init(self):
        super().init()
        # 1. Fix missing dossier_id from entry_id
        self.env.cr.execute("""
            UPDATE logistique_dossier_cheque ldc
            SET dossier_id = le.dossier_id
            FROM logistique_entry le
            WHERE ldc.entry_id = le.id
            AND ldc.dossier_id IS NULL
        """)
        # 2. Fix missing ste_id from dossier_id
        self.env.cr.execute("""
            UPDATE logistique_dossier_cheque ldc
            SET ste_id = ld.ste_id
            FROM logistique_dossier ld
            WHERE ldc.dossier_id = ld.id
            AND ldc.ste_id IS NULL
        """)

    @api.onchange('entry_id')
    def _onchange_entry_id(self):
        for rec in self:
            if rec.entry_id:
                rec.ste_id = rec.entry_id.ste_id
                rec.dossier_id = rec.entry_id.dossier_id

    @api.constrains('entry_id', 'amount', 'type', 'date', 'beneficiary_id')
    def _check_entry_status(self):
        if self.env.context.get('from_bot'):
            return
        for rec in self:
            if rec.entry_id and rec.entry_id.status == 'in_progress':
                raise ValidationError("Vous ne pouvez pas ajouter ou modifier des paiements tant que le dossier est 'En cours'. Veuillez d'abord le passer en 'Gate Out'.")
