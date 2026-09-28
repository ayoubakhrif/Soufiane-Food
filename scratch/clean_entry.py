import re

filepath = r"c:\odoo-repos\Soufiane-Food\gestion_stock_app_casa\lib\screens\stock_entry_screen.dart"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# remove variable declarations
content = re.sub(r"List<GarageItem>\s*_garages\s*=\s*\[\];\n?", "", content)
content = re.sub(r"String\?\s*_selectedGarage;\n?", "", content)

# remove _garages extraction
content = re.sub(r"_garages\s*=\s*data\['garages'\];\n?", "", content)
content = re.sub(r"if\s*\(_garages\.isNotEmpty\)\s*\{\s*_selectedGarage\s*=\s*_garages\.first\.key;\s*\}\n?", "", content)

# remove dropdown from UI
dropdown_pattern = r"// Garage[\s\S]*?DropdownButtonFormField<String>\([\s\S]*?onChanged: \(val\) => setState\(\(\) => _selectedGarage = val\),[\s\S]*?\),\s*const SizedBox\(height: 14\),"
content = re.sub(dropdown_pattern, "", content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Entry Screen cleaned.")
