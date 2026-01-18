from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class CoreVehicle(models.Model):
    _name = 'core.vehicle'
    _description = 'Véhicule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'matricule'

    matricule = fields.Char(string='Matricule', required=True, tracking=True)
    photo = fields.Image(string='Photo')
    marque = fields.Char(string='Marque', required=True, tracking=True)
    p_achat = fields.Float(string="Prix d'achat", tracking=True)
    
    driver_id = fields.Many2one(
        'core.employee', 
        string='Chauffeur', 
        domain="[('job_id.name', '=', 'Driver')]",
        tracking=True
    )
    
    site = fields.Char(string='Site', tracking=True)
    gps = fields.Char(string='GPS', tracking=True)
    in_repair = fields.Boolean(string='En réparation', default=False, tracking=True)
    registration_card_number = fields.Char(string='Numéro carte grise', tracking=True)

    document_ids = fields.One2many('core.vehicle.document', 'vehicle_id', string='Documents')


class CoreVehicleDocument(models.Model):
    _name = 'core.vehicle.document'
    _description = 'Document Véhicule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    vehicle_id = fields.Many2one('core.vehicle', string='Véhicule', required=True, ondelete='cascade')
    
    doc_type = fields.Selection([
        ('carte_verte', 'Carte verte'),
        ('carte_grise', 'Carte grise'),
        ('visite_technique', 'Visite technique'),
        ('talon_observation', "Talon d'observation"),
        ('vignette', 'Vignette'),
    ], string='Type de document', required=True, tracking=True)
    
    expiration_date = fields.Date(string="Date d'expiration", required=True, tracking=True)
    drive_url = fields.Char(string='Lien Drive', required=True, help="Lien Google Drive / OneDrive vers le document")
    note = fields.Text(string='Note')

    # Computed fields for expiration tracking (Cards)
    days_remaining = fields.Integer(
        string='Jours restants',
        compute='_compute_expiration_info',
        store=False
    )
    is_expired = fields.Boolean(
        string='Est expiré',
        compute='_compute_expiration_info',
        store=False
    )

    @api.depends('expiration_date')
    def _compute_expiration_info(self):
        today = fields.Date.today()
        for doc in self:
            if doc.expiration_date:
                delta = (doc.expiration_date - today).days
                doc.days_remaining = delta
                doc.is_expired = delta < 0
            else:
                doc.days_remaining = 0
                doc.is_expired = False
