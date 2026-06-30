
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
