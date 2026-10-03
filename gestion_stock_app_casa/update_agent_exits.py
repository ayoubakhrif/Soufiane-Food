import sys

with open("lib/screens/agent_exits_list_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "Text('Date: ${exit['date']}'),",
    "Text('Date: ${exit['date']}'),\n                          Text('Chauffeur: ${exit['driver_name'] ?? \"Pas de chauffeur\"}'),"
)

with open("lib/screens/agent_exits_list_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Added driver_name to agent exits list")
