from odoo import models, fields, api

class AIAlias(models.Model):
    _name = 'ai.alias'
    _description = 'AI Alias / Synonym'
    _order = 'usage_count desc, id desc'

    input_text = fields.Char(string='Texte Utilisateur', required=True, index=True)
    model_name = fields.Char(string='Modèle Cible', required=True)
    record_id = fields.Integer(string='ID Enregistrement', required=True)
    usage_count = fields.Integer(string="Compteur d'utilisation", default=0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('input_model_unique', 'unique(input_text, model_name)', 'Cet alias existe déjà pour ce modèle.')
    ]

class AIInteractionLog(models.Model):
    _name = 'ai.interaction.log'
    _description = 'AI Interaction Log'
    _order = 'create_date desc'

    source = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('api', 'API Externe'),
        ('other', 'Autre')
    ], string='Source', required=True, default='api')
    
    raw_message = fields.Text(string='Message Brut')
    parsed_payload = fields.Text(string='Payload Analysé')
    validation_result = fields.Text(string='Résultat Validation')
    user_identifier = fields.Char(string='Identifiant Utilisateur')
