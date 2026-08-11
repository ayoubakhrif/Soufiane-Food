from odoo import models, fields, api
from datetime import timedelta

class Finance2Cheque(models.Model):
    _name = 'finance2.cheque'
    _description = 'Chèque Physique (Finance 2)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='N° Chèque', required=True, tracking=True)
    ste_id = fields.Many2one('finance2.ste', string='Société', required=True, tracking=True)
    benif_id = fields.Many2one('finance2.benif', string='Bénéficiaire', tracking=True)
    
    amount_total = fields.Float(string='Montant Total', tracking=True)
    
    type = fields.Selection([('cheque', 'Chèque'), ('effet', 'Effet')], string='Type', default='cheque', tracking=True)
    chq_certifie = fields.Boolean(string='Chq certifié', tracking=True)
    journal = fields.Char(string='Journal', tracking=True)
    personne_id = fields.Many2one('finance2.personne', string='Personnes', tracking=True)
    serie_facture = fields.Char(string='Série de facture', tracking=True)
    
    date_emission = fields.Date(string="Date d'émission", tracking=True)
    date_echeance = fields.Date(string="Date d'échéance", tracking=True)
    date_encaissement = fields.Date(string="Date d'encaissement", tracking=True)
    
    commentaire = fields.Text(string="Commentaire")
    
    # Documents
    chq_vide_pdf = fields.Binary(string='Chèque vide (PDF)', attachment=True)
    chq_vide_filename = fields.Char(string='Nom du fichier Chèque vide')
    
    doc_pdf = fields.Binary(string='Documentation (PDF)', attachment=True)
    doc_filename = fields.Char(string='Nom du fichier Documentation')
    
    # Workflow Status
    state = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('reserve', 'Réserve'),
        ('actif', 'Actif'),
        ('cloture', 'Clôturé'),
        ('annule', 'Annulé'),
    ], string='État', default='brouillon', tracking=True, required=True)
    
    # Suivi Logistique
    remis_a_id = fields.Many2one('finance2.personne', string='Remis à', tracking=True)
    date_remise = fields.Date(string='Date de remise (Actif)', tracking=True)
    
    # Répartitions
    repartition_ids = fields.One2many('finance2.repartition', 'cheque_id', string='Répartitions')

    @api.model
    def create(self, vals):
        # Additional logic from the bot creation can be placed here if necessary
        return super(Finance2Cheque, self).create(vals)
        
    def action_confirmer(self):
        for rec in self:
            rec.state = 'reserve'
            
    def action_remettre_finance(self):
        for rec in self:
            rec.state = 'brouillon'
            rec.remis_a_id = False
            rec.date_remise = False
            
    def action_mettre_actif(self):
        for rec in self:
            if not rec.remis_a_id:
                # Odoo will show a validation error if not present when required in view, 
                # but we can enforce it here too
                pass
            rec.state = 'actif'
            rec.date_remise = fields.Date.today()
            
    def action_cloturer(self):
        for rec in self:
            rec.state = 'cloture'
            
    def action_annuler(self):
        for rec in self:
            rec.state = 'annule'

    @api.model
    def _cron_check_actif_5_days(self):
        """Cron job that checks for cheques in 'actif' state for more than 5 days and sends a reminder."""
        limit_date = fields.Date.today() - timedelta(days=5)
        cheques = self.search([
            ('state', '=', 'actif'),
            ('date_remise', '<=', limit_date)
        ])
        for cheque in cheques:
            # Send message to chatter
            cheque.message_post(
                body=f"Rappel : Ce chèque est à l'état Actif depuis plus de 5 jours (remis le {cheque.date_remise}).",
                subtype_xmlid='mail.mt_note'
            )


class Finance2Repartition(models.Model):
    _name = 'finance2.repartition'
    _description = 'Répartition de Chèque'

    cheque_id = fields.Many2one('finance2.cheque', string='Chèque', required=True, ondelete='cascade')
    amount = fields.Float(string='Montant', required=True)
    serie_facture = fields.Char(string='Série de facture')
    bl = fields.Char(string='BL')
    journal = fields.Char(string='Journal')
