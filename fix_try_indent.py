import os

filepath = 'custom-addons/finance_2/controllers/whatsapp_finance_api.py'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.strip() == "import io" and "import xlsxwriter" in lines[i+1]:
        # found the start
        lines.insert(i, "            try:\r\n")
        # indent all lines until line 819
        for j in range(i+1, 820):
            lines[j] = "    " + lines[j]
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Fixed indentation for try block")
