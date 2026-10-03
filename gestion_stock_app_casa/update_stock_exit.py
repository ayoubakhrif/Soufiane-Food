import sys

with open("lib/screens/stock_exit_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

# Replace validation
content = content.replace(
    "if (_selectedDriver == null) {\n      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sÃ©lectionner un chauffeur')));\n      return;\n    }",
    ""
)
content = content.replace(
    "if (_selectedDriver == null) {\n      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez sélectionner un chauffeur')));\n      return;\n    }",
    ""
)
content = content.replace(
    "if (_selectedDriver == null) {\n      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Veuillez s\\u00e9lectionner un chauffeur')));\n      return;\n    }",
    ""
)

# Fix Button
content = content.replace("Valider la tournÃ©e", "Enregistrer")
content = content.replace("Valider la tournée", "Enregistrer")

# Remove Driver Dropdown UI
import re
# Find the Column children where the Driver dropdown is
pattern = r"DropdownButtonFormField<DriverItem>\(.*?labelText: '1\. Chauffeur \(Camion\)'.*?onChanged:.*?,\n\s*\),"
content = re.sub(pattern, "", content, flags=re.DOTALL)

with open("lib/screens/stock_exit_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated stock_exit_screen.dart")
