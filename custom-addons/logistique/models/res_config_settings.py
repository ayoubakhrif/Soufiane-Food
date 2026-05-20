from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    maersk_consumer_key = fields.Char(
        string='Maersk Consumer Key',
        config_parameter='maersk.consumer_key'
    )
    maersk_consumer_secret = fields.Char(
        string='Maersk Consumer Secret',
        config_parameter='maersk.consumer_secret'
    )
