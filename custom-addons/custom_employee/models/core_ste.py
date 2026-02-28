from odoo import models, fields

class CoreSte(models.Model):
    _name = 'core.ste'
    _description = 'Société'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']

    name = fields.Char(string='Raison social', required=True, tracking=True)
    code = fields.Char(string='Code', tracking=True)
    manager_name = fields.Char(string='Nom de gérant', tracking=True)
    rc = fields.Char(string='R.C', tracking=True)
    ice = fields.Char(string='I.C.E', tracking=True)
    if_field = fields.Char(string='I.F', tracking=True)
    address = fields.Text(string='Address')
    is_zone_franche = fields.Boolean(string='Zone Franche', default=False, tracking=True)
    
    # image_1920 is inherited from image.mixin
