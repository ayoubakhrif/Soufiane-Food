import os

filepath = "whatsapp_bridge/index.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "pdfFiles.push({ base64: base64Data, name: file.file_name });",
    "pdfFiles.push({ base64: base64Data, name: file.file_name, caption: file.caption });"
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("Node.js patched for caption.")
