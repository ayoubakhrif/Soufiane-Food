import os

filepath = "custom-addons/generate_bons/report/bon_report_templates.xml"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    '<td><span t-field="line.qte"/></td>',
    '<td><span t-esc="int(line.qte)"/></td>'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)
print("pdf updated")
