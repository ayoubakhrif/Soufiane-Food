from odoo import models, fields, api

class FridgeEquipment(models.Model):
    _name = 'fridge.equipment'
    _description = 'Equipement Frigo'

    name = fields.Char(string="Nom / Référence", required=True)
    capacity_tonnes = fields.Float(string="Capacité Totale (Tonnes)", required=True)
    target_temperature = fields.Char(string="Température Cible")
    
    ledger_ids = fields.One2many('fridge.ledger', 'fridge_id', string="Mouvements")
    
    current_load_tonnes = fields.Float(
        string="Tonnage Actuel", 
        compute='_compute_load',
        store=True
    )
    available_capacity_tonnes = fields.Float(
        string="Espace Disponible", 
        compute='_compute_load',
        store=True
    )

    @api.depends('ledger_ids.tonnes', 'ledger_ids.operation_type', 'capacity_tonnes')
    def _compute_load(self):
        for record in self:
            total_in = sum(record.ledger_ids.filtered(lambda l: l.operation_type == 'in').mapped('tonnes'))
            total_out = sum(record.ledger_ids.filtered(lambda l: l.operation_type == 'out').mapped('tonnes'))
            current_load = total_in - total_out
            
            record.current_load_tonnes = current_load
            record.available_capacity_tonnes = record.capacity_tonnes - current_load
