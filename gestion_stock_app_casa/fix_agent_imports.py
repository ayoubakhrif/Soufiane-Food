import sys

with open("lib/screens/agent_exits_list_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("import '../models/driver_item.dart';", "import '../models/item_models.dart';")
content = content.replace(
    "final drvs = await ApiService.fetchDrivers();",
    "final bootstrap = await ApiService.fetchBootstrap();\n      final drvs = bootstrap['drivers'] as List<DriverItem>;"
)
content = content.replace("value: d, child: Text(d.name)", "value: d, child: Text(d.name!)")

with open("lib/screens/agent_exits_list_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated agent_exits_list_screen.dart imports and fetch")
