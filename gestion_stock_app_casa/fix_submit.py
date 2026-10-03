import sys

with open("lib/screens/stock_exit_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("DriverItem? _selectedDriver;", "")
content = content.replace(
    "final orderRef = 'TOUR-${_selectedDriver!.name.toUpperCase()}-$date-${DateTime.now().millisecondsSinceEpoch}';",
    "final orderRef = 'TOUR-$date-${DateTime.now().millisecondsSinceEpoch}';"
)
content = content.replace("'driver_id': _selectedDriver!.id,", "'driver_id': 0,")

with open("lib/screens/stock_exit_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed _submit NPE")
