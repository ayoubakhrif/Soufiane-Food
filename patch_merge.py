import os

filepath = "whatsapp_bridge/index.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Update the merge condition
old_code = "if (pdfFiles.length === 1) {"
new_code = "if (pdfFiles.length === 1 || result.merge_pdfs === false) {\n                                    for (const pdfFile of pdfFiles) {\n                                        await sock.sendMessage(from, {\n                                            document: Buffer.from(pdfFile.base64, 'base64'),\n                                            mimetype: 'application/pdf',\n                                            fileName: pdfFile.name,\n                                            caption: pdfFile.caption || `Document pour *${identifier}*.`\n                                        }, { quoted: msg });\n                                    }\n                                } else {"

if "result.merge_pdfs === false" not in content:
    content = content.replace(old_code, new_code)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("index.js patched with merge_pdfs flag.")
else:
    print("Already patched.")
