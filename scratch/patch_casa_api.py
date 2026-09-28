import re

filepath = r"c:\odoo-repos\Soufiane-Food\custom-addons\stock_casa_field\controllers\api_stock.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

login_method = """
    @http.route('/api/casa/login', type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({'status': 'ok'})
        data = self._get_request_data()
        phone = (data.get('phone') or '').strip()
        password = (data.get('password') or '').strip()

        if not phone or not password:
            return self._json_response({'status': 'error', 'message': 'Veuillez saisir le numéro de téléphone et le mot de passe.'}, status=400)

        # On se connecte via le chauffeur (driver) pour Casa puisque le modele agent n'existe pas
        driver = request.env['casa_field.stock.driver'].sudo().search([('phone', '=', phone)], limit=1)
        if driver and driver.password == password:
            return self._json_response({'status': 'success', 'agent': {'id': driver.id, 'name': driver.name, 'phone': driver.phone, 'role': 'driver'}})

        return self._json_response({'status': 'error', 'message': 'Numero de telephone ou mot de passe incorrect.'}, status=401)
"""

if "def api_login" not in content:
    content = content.replace("    @http.route('/api/casa/bootstrap',", login_method + "\n    @http.route('/api/casa/bootstrap',")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added login endpoint.")
else:
    print("Login endpoint already exists.")
