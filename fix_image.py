import sys

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "r", encoding="utf-8") as f:
    content = f.read()

old_code = """        data = []
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        for rec in exits:
            image_url = ""
            if rec.product_id and rec.product_id.image_emballage:
                image_url = f"{base_url}/web/image?model=casa_field.stock.product&id={rec.product_id.id}&field=image_emballage\""""

new_code = """        data = []
        base_url = 'https://gestia-soufianefoods.cloud'
        
        for rec in exits:
            image_url = ""
            if rec.product_id:
                image_url = f"{base_url}/web/image?model=casa_field.stock.product&id={rec.product_id.id}&field=image_emballage\""""

content = content.replace(old_code, new_code)

with open("custom-addons/stock_casa_field/controllers/api_stock.py", "w", encoding="utf-8") as f:
    f.write(content)
