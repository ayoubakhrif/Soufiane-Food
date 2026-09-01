import os

filepath = "custom-addons/tanger_med/security/ir.model.access.csv"
with open(filepath, 'rb') as f:
    content = f.read()
if content.startswith(b'\xef\xbb\xbf'):
    with open(filepath, 'wb') as f:
        f.write(content[3:])
    print("Removed BOM")
else:
    print("No BOM found")
