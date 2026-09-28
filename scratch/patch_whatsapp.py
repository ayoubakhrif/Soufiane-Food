import os

file_path = r"c:\odoo-repos\Soufiane-Food\custom-addons\stock_casa_field\controllers\api_stock.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

whatsapp_code = """
            try:
                driver_name = request.env['casa_field.stock.driver'].sudo().browse(driver_id).name if driver_id else "Inconnu"
                msg = f"🚚 *Nouvelle Tournée Validée (Casa)*\\n"
                msg += f"Réf: {order_ref}\\n"
                msg += f"Chauffeur: {driver_name}\\n"
                msg += f"Nombre de sorties: {len(lines)}\\n\\n"
                
                for line in lines:
                    product = request.env['product.product'].sudo().browse(int(line.get('product_id'))).name
                    client_id = line.get('client_id')
                    client = request.env['casa_field.stock.client'].sudo().browse(int(client_id)).name if client_id else "Inconnu"
                    qty = line.get('qty', 0)
                    msg += f"- {product} ({qty} u) -> {client}\\n"
                
                payload = {
                    "group_id": "120363049891261462@g.us",
                    "text": msg
                }
                import requests
                requests.post("http://172.17.0.1:3000/api/send", json=payload, timeout=5)
            except Exception as e:
                _logger.error(f"WhatsApp send error: {str(e)}")
"""

if "120363049891261462@g.us" not in content:
    content = content.replace(
        "            return self._json_response({'status': 'success', 'message': f'{len(created_exits)} sorties crées avec succès.'})",
        whatsapp_code + "\n            return self._json_response({'status': 'success', 'message': f'{len(created_exits)} sorties crées avec succès.'})"
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("WhatsApp logic injected successfully.")
else:
    print("WhatsApp logic already exists.")
