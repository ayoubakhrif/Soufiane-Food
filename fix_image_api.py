import sys

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace image_url logic
old_image_logic = """        base_url = 'https://gestia-soufianefoods.cloud'
        
        for rec in exits:
            image_url = ""
            if rec.product_id:
                image_url = f"{base_url}/web/image?model=casa_field.stock.product&id={rec.product_id.id}&field=image_emballage\""""

new_image_logic = """        base_url = 'https://gestia-soufianefoods.cloud'
        
        for rec in exits:
            image_url = ""
            if rec.lot and rec.product_id:
                entry = request.env['casa_field.stock.entry'].sudo().search([
                    ('product_id', '=', rec.product_id.id),
                    ('lot', '=', rec.lot)
                ], limit=1)
                if entry and entry.photo_packaging:
                    image_url = f"{base_url}/api/casa/image/casa_field.stock.entry/{entry.id}/photo_packaging\""""

content = content.replace(old_image_logic, new_image_logic)

# Add image serving route
image_route = """

    @http.route('/api/casa/image/<string:model>/<int:id>/<string:field>', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def api_image(self, model, id, field, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
            
        try:
            record = request.env[model].sudo().browse(id)
            if not record.exists():
                return request.not_found()
                
            image_base64 = getattr(record, field)
            if not image_base64:
                return request.not_found()
                
            import base64
            image_data = base64.b64decode(image_base64)
            headers = [('Content-Type', 'image/jpeg')]
            return request.make_response(image_data, headers=headers)
        except Exception as e:
            return request.not_found()
"""

# Append route just before api_return
content = content.replace(
    "    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')",
    image_route + "\n    @http.route('/api/casa/return', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')"
)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
