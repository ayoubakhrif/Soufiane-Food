import os
import re

base_dir = r"c:\odoo-repos\Soufiane-Food\gestion_stock_app_casa\lib"

# 1. Fix 'stock_casa_field' -> 'stock_casa' for frigo
def replace_in_file(filepath, old_str, new_str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_str in content:
        new_content = content.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Replaced {old_str} in {filepath}")

replace_in_file(os.path.join(base_dir, 'models', 'stock_card.dart'), "'stock_casa_field'", "'stock_casa'")
replace_in_file(os.path.join(base_dir, 'screens', 'stock_entry_screen.dart'), "'stock_casa_field'", "'stock_casa'")
replace_in_file(os.path.join(base_dir, 'screens', 'stock_exit_screen.dart'), "'stock_casa_field'", "'stock_casa'")


# 2. Remove Transfer button from HomeScreen
home_file = os.path.join(base_dir, 'screens', 'home_screen.dart')
with open(home_file, 'r', encoding='utf-8') as f:
    home_content = f.read()

# remove the transfer button code block
home_content = re.sub(r"// 3\. Transfert Garage.*?_buildActionButton\([\s\S]*?\}\),\s*\),", "", home_content, flags=re.DOTALL)
# remove import of transfer screen
home_content = re.sub(r"import 'stock_transfer_screen\.dart';\n?", "", home_content)

with open(home_file, 'w', encoding='utf-8') as f:
    f.write(home_content)


# 3. Clean Entry Screen
entry_file = os.path.join(base_dir, 'screens', 'stock_entry_screen.dart')
with open(entry_file, 'r', encoding='utf-8') as f:
    entry_content = f.read()

# remove _selectedGarage
entry_content = re.sub(r"String\? _selectedGarage;\n", "", entry_content)
entry_content = re.sub(r"List<Map<String, dynamic>> _garages = \[\];\n", "", entry_content)
entry_content = re.sub(r"_garages = List<Map<String, dynamic>>\.from\(data\['garages'\] \?\? \[\]\);\n\s*if \(_garages\.isNotEmpty\) \{\n\s*_selectedGarage = _garages\.first\['key'\];\n\s*\}\n", "", entry_content)

# Regex to safely remove the Garage dropdown from UI building
# In stock_entry_screen.dart, it looks like:
# _garages.isNotEmpty ? DropdownButtonFormField<String>(...) : const SizedBox.shrink(),
# or something similar. Let's do a more robust replace.
entry_content = re.sub(r"DropdownButtonFormField<String>\([\s\S]*?value: _selectedGarage,[\s\S]*?items: _garages[\s\S]*?onChanged:[\s\S]*?\}\),\s*const SizedBox\(height: 16\),", "", entry_content)
# Or if it's simpler:
entry_content = re.sub(r"// Garage de réception[\s\S]*?DropdownButtonFormField<String>\([\s\S]*?onChanged:\s*\(val\)[\s\S]*?\}\),[\s\S]*?const SizedBox\(height: 16\),", "", entry_content)
# Let's just remove anything mentioning _garages or _selectedGarage in the build tree
entry_content = re.sub(r"DropdownButtonFormField<String>\(\s*decoration:\s*InputDecoration\(\s*labelText:\s*'Garage de réception'.*?onChanged:\s*\(val\).*?\}\),\s*const SizedBox\(height: 16\),", "", entry_content, flags=re.DOTALL)

# remove payload 'garage'
entry_content = re.sub(r"'garage': _selectedGarage,\n", "", entry_content)

with open(entry_file, 'w', encoding='utf-8') as f:
    f.write(entry_content)


# 4. Clean Exit Screen
exit_file = os.path.join(base_dir, 'screens', 'stock_exit_screen.dart')
with open(exit_file, 'r', encoding='utf-8') as f:
    exit_content = f.read()

# Remove the text showing garage
exit_content = re.sub(r"if \(card\.garage\.isNotEmpty\)\s*Text\(\s*'Garage: \$\{card\.garage\}',[\s\S]*?\),", "", exit_content)
# Payload
exit_content = re.sub(r"'garage': _selectedCard!\.garage,\n", "", exit_content)

with open(exit_file, 'w', encoding='utf-8') as f:
    f.write(exit_content)


# 5. Clean Stock Card Model
card_file = os.path.join(base_dir, 'models', 'stock_card.dart')
with open(card_file, 'r', encoding='utf-8') as f:
    card_content = f.read()

card_content = re.sub(r"final String garage;\n", "", card_content)
card_content = re.sub(r"\s*required this\.garage,\n", "\n", card_content)
card_content = re.sub(r"\s*garage: json\['garage'\] \?\? '',\n", "\n", card_content)

with open(card_file, 'w', encoding='utf-8') as f:
    f.write(card_content)

print("Flutter cleaned from garage and frigo value fixed.")
