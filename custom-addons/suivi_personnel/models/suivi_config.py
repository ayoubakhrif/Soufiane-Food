from odoo import models, fields, api

class SuiviConfig(models.Model):
    _name = 'suivi.config'
    _description = 'Suivi Personnel Configuration'

    name = fields.Char(string='Configuration', default='Paramètres', required=True)
    month_start_day = fields.Integer(
        string='Jour de début du mois',
        default=1,
        required=True,
        help="Définit le jour du mois où commence la période comptable (ex: 1, 2, 15, etc.)"
    )

    @api.model
    def get_config(self):
        """Retrieve or create the singleton configuration record"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Paramètres', 'month_start_day': 1})
        return config

    @api.constrains('month_start_day')
    def _check_month_start_day(self):
        for rec in self:
            if rec.month_start_day < 1 or rec.month_start_day > 31:
                raise models.ValidationError("Le jour de début doit être entre 1 et 31")

    def open_settings(self):
        """Helper to open the form view of the singleton"""
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Paramètres Généraux',
            'res_model': 'suivi.config',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'inline',
        }
