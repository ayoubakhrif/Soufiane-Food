init_path = 'custom-addons/tanger_med/models/__init__.py'
with open(init_path, 'r', encoding='utf-8') as f:
    content = f.read()
if 'finance2_cheque_inherit' not in content:
    content += '\nfrom . import finance2_cheque_inherit\n'
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(content)
