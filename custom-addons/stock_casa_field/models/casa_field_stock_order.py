from odoo import models, fields, api

class CasaStockOrder(models.Model):
    _name = 'casa_field.stock.order'
    _description = 'Commande de Chargement'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='Nouveau')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    commercial_id = fields.Many2one('casa_field.stock.agent', string='Commercial', required=True, domain=[('role', '=', 'commercial')])
    client_id = fields.Many2one('casa_field.stock.client', string='Client', required=True)
    state = fields.Selection([
        ('pending', 'En attente'),
        ('done', 'Prepare')
    ], string='Statut', default='pending', required=True)
    
    line_ids = fields.One2many('casa_field.stock.order.line', 'order_id', string='Lignes de Commande')

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouveau') == 'Nouveau':
            vals['name'] = self.env['ir.sequence'].next_by_code('casa_field.stock.order') or 'Nouveau'
        order = super(CasaStockOrder, self).create(vals)
        order._send_whatsapp_notification()
        return order

    def _send_whatsapp_notification(self):
        import requests
        import logging
        _logger = logging.getLogger(__name__)
        
        for order in self:
            try:
                commercial_name = order.commercial_id.name if order.commercial_id else 'Commercial'
                client_name = order.client_id.name if order.client_id else 'Client Inconnu'
                
                total_tonnage = sum(line.tonnage for line in order.line_ids)
                
                msg = f"Nelle Commande: *{order.name}*\n"
                msg += f"Commercial: *{commercial_name}*\n"
                msg += f"Client: *{client_name}*\n\n"
                msg += "Détails:\n"
                for line in order.line_ids:
                    msg += f"- {line.product_id.name}: {line.quantity} colis | {line.weight} Kg ({line.tonnage} Kg total)\n"
                    if line.note:
                        msg += f"  (Note: {line.note})\n"
                msg += f"\n*Tonnage Total: {total_tonnage} Kg*\n\n"
                msg += f"Merci {commercial_name} pour cette commande ! 👏"
                
                payload = {
                    "group_id": "120363049891261462@g.us",
                    "text": msg
                }
                
                # Using the local node.js whatsapp bot api endpoint
                requests.post("http://172.17.0.1:3000/api/send", json=payload, timeout=5)
            except Exception as e:
                _logger.error(f"Failed to send WhatsApp notification for order {order.name}: {str(e)}")


class CasaStockOrderLine(models.Model):
    _name = 'casa_field.stock.order.line'
    _description = 'Ligne de Commande de Chargement'

    order_id = fields.Many2one('casa_field.stock.order', string='Commande', required=True, ondelete='cascade')
    product_id = fields.Many2one('casa_field.stock.product', string='Produit', required=True)
    quantity = fields.Float(string='Quantite (Unites)', required=True, default=1.0)
    weight = fields.Float(string='Poids Unitaire (Kg)', required=True, default=0.0)
    tonnage = fields.Float(string='Tonnage Total (Kg)', compute='_compute_tonnage', store=True)
    note = fields.Text(string='Note Specifique')

    @api.depends('quantity', 'weight')
    def _compute_tonnage(self):
        for line in self:
            line.tonnage = line.quantity * line.weight
