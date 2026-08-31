import os

filepath = "whatsapp_bridge/index.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# I will replace the whole block manually
start_marker = "if (pdfFiles.length === 1) {"
end_marker = "} else {"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    new_block = """if (pdfFiles.length === 1 || result.merge_pdfs === false) {
                                    for (const pdfFile of pdfFiles) {
                                        await sock.sendMessage(from, {
                                            document: Buffer.from(pdfFile.base64, 'base64'),
                                            mimetype: 'application/pdf',
                                            fileName: pdfFile.name,
                                            caption: pdfFile.caption || `Document pour *${identifier}*.`
                                        }, { quoted: msg });
                                    }
                                """
    
    content = content[:start_idx] + new_block + content[end_idx:]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Syntax patched")
