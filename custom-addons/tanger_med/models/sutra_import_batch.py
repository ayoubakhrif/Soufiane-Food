from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SutraImportBatch(models.Model):
    _name = 'sutra.import.batch'
    _description = "Lot d'importation SUTRA"
    _order = 'create_date desc'

    name = fields.Char(string='Nom du Lot', required=True, default=lambda self: _('Nouveau Lot'))
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Traite')
    ], string='Statut', default='draft', tracking=True)
    
    line_ids = fields.One2many('sutra.import.line', 'batch_id', string='Lignes')
    
    total_lines = fields.Integer(string='Total Lignes', compute='_compute_stats')
    valid_lines = fields.Integer(string='Lignes Valides', compute='_compute_stats')
    error_lines = fields.Integer(string='Lignes en Erreur', compute='_compute_stats')

    @api.depends('line_ids', 'line_ids.status')
    def _compute_stats(self):
        for rec in self:
            rec.total_lines = len(rec.line_ids)
            rec.valid_lines = len(rec.line_ids.filtered(lambda l: l.status == 'ready'))
            rec.error_lines = len(rec.line_ids.filtered(lambda l: l.status == 'error'))

    def action_verify(self):
        for line in self.line_ids.filtered(lambda l: l.status in ['draft', 'error']):
            line._check_dum()

    def action_process(self):
        self.ensure_one()
        self.action_verify()
        
        ready_lines = self.line_ids.filtered(lambda l: l.status == 'ready')
        if not ready_lines:
            raise UserError("Il n'y a aucune ligne valide a traiter.")

        factures_creees = 0
        for line in ready_lines:
            # Create or get Sutra Dossier
            sutra_dossier = self.env['sutra.dossier'].search([('logistics_id', '=', line.logistics_id.id)], limit=1)
            if not sutra_dossier:
                sutra_dossier = self.env['sutra.dossier'].create({
                    'logistics_id': line.logistics_id.id,
                })
            
            # Check if invoice exists
            existing_facture = self.env['sutra.facture'].search([
                ('sutra_id', '=', sutra_dossier.id),
                ('name', '=', line.facture_name)
            ])
            if existing_facture:
                line.status = 'error'
                line.error_msg = 'Facture existante dans ce dossier.'
                continue
            
            # Create Invoice
            self.env['sutra.facture'].create({
                'sutra_id': sutra_dossier.id,
                'name': line.facture_name,
                'date': line.date,
                'amount': line.amount,
                'state': 'non_paye'
            })
            
            line.status = 'done'
            line.error_msg = ''
            factures_creees += 1

        if self.valid_lines == 0 and self.error_lines == 0:
            self.state = 'done'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Traitement termine',
                'message': f"{factures_creees} factures creees avec succes.",
                'type': 'success',
                'sticky': False,
            }
        }

class SutraImportLine(models.Model):
    _name = 'sutra.import.line'
    _description = "Ligne d'importation SUTRA"

    batch_id = fields.Many2one('sutra.import.batch', string='Lot', required=True, ondelete='cascade')
    dum = fields.Char(string='Numero DUM', required=True)
    facture_name = fields.Char(string='Numero de Facture', required=True)
    date = fields.Date(string='Date')
    amount = fields.Float(string='Montant TTC')
    
    logistics_id = fields.Many2one('logistique.entry', string='Dossier Trouve', readonly=True)
    status = fields.Selection([
        ('draft', 'Brouillon'),
        ('ready', 'Pret'),
        ('error', 'Erreur'),
        ('done', 'Importe')
    ], string='Statut', default='draft', readonly=True)
    error_msg = fields.Char(string='Message', readonly=True)

    @api.onchange('dum')
    def _onchange_dum(self):
        if self.dum:
            self._check_dum()

    def _check_dum(self):
        for rec in self:
            if not rec.dum:
                rec.status = 'error'
                rec.error_msg = 'DUM manquant'
                continue
                
            if rec.status == 'done':
                continue
                
            entry = self.env['logistique.entry'].search(['|', ('tanger_med_dum', '=', rec.dum), ('dum', '=', rec.dum)], limit=1)
            if entry:
                rec.logistics_id = entry.id
                rec.status = 'ready'
                rec.error_msg = ''
            else:
                rec.logistics_id = False
                rec.status = 'error'
                rec.error_msg = 'DUM introuvable'
