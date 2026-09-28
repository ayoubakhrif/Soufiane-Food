import os
import re

base_dir = r"c:\odoo-repos\Soufiane-Food\gestion_stock_app_casa\lib"

# 1. home_screen.dart
home = os.path.join(base_dir, 'screens', 'home_screen.dart')
with open(home, 'r', encoding='utf-8') as f:
    content = f.read()

# completely remove the transfer button
content = re.sub(r"_buildActionButton\(\s*title:\s*'Transfert entre Garages'[\s\S]*?\}\),\s*", "", content)
with open(home, 'w', encoding='utf-8') as f:
    f.write(content)

# 2. stock_exit_screen.dart
exit_file = os.path.join(base_dir, 'screens', 'stock_exit_screen.dart')
with open(exit_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r"String _selectedGarageFilter = 'ALL';\n?", "", content)
content = re.sub(r"final garagesAvailable = \['ALL', \.\.\._stockList\.map\(\(e\) => e\.garage\)\.toSet\(\)\.toList\(\)\];\n?", "", content)
content = re.sub(r"DropdownButton<String>\([\s\S]*?value: _selectedGarageFilter,[\s\S]*?onChanged:[\s\S]*?\}\),\s*", "", content)
content = re.sub(r"final matchesGarage = _selectedGarageFilter == 'ALL' \|\| item\.garage == _selectedGarageFilter;\n", "final matchesGarage = true;\n", content)
content = re.sub(r"•\s*Garage:\s*\$\{item\.garage\.toUpperCase\(\)\}", "", content)
content = re.sub(r"'garage':\s*item\.garage,\n", "", content)

with open(exit_file, 'w', encoding='utf-8') as f:
    f.write(content)

# 3. models/stock_card.dart
model_file = os.path.join(base_dir, 'models', 'stock_card.dart')
with open(model_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r"garage:\s*json\['garage'\].*?,\n?", "", content)
with open(model_file, 'w', encoding='utf-8') as f:
    f.write(content)

# 4. widgets/stock_card_item.dart
widget_file = os.path.join(base_dir, 'widgets', 'stock_card_item.dart')
with open(widget_file, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r"Container\(\s*padding:\s*const EdgeInsets.*?\n\s*decoration:[\s\S]*?Text\(\s*item\.garage\.toUpperCase\(\),[\s\S]*?\)[\s\S]*?\),", "", content)

with open(widget_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed compile errors.")
