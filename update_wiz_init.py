init_path = 'custom-addons/tanger_med/wizard/__init__.py'
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()
if 'sutra_facture_pay_wizard' not in content:
    content += '\nfrom . import sutra_facture_pay_wizard\n'
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(content)
