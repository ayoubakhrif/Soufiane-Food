import sys

with open("lib/screens/agent_exits_list_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("d.name!", "d.name")

with open("lib/screens/agent_exits_list_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
