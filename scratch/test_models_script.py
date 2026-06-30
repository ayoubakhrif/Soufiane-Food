import xmlrpc.client
import requests
import sys

def get_odoo_param():
    try:
        # We need to read from the odoo config file directly if we can't use xmlrpc easily,
        # but the easiest way is to run a small odoo shell script.
        pass
    except Exception as e:
        print(e)

code = """
import requests
api_key = env['ir.config_parameter'].sudo().get_param('tresorerie_chq.gemini_key')
if not api_key:
    print("NO API KEY")
else:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    resp = requests.get(url)
    if resp.status_code == 200:
        models = [m['name'] for m in resp.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        print("AVAILABLE MODELS:")
        for m in models:
            print(m)
    else:
        print("ERROR:", resp.text)
"""
with open('test_models.py', 'w') as f:
    f.write(code)
