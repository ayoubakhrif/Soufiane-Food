import sys
import re

with open("lib/screens/exits_history_screen.dart", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("  @override\n  Future<void> _deliverExit", "  Future<void> _deliverExit")

with open("lib/screens/exits_history_screen.dart", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed override")
