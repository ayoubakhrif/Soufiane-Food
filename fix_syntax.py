import os

filepath = "whatsapp_bridge/index.js"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# I will replace the whole block manually
start_marker = "if (pdfFiles.length > 0) {"
end_marker = "if (nonPdfFiles.length > 0) {"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_block = """if (pdfFiles.length > 0) {
                                if (pdfFiles.length === 1 || result.merge_pdfs === false) {
                                    for (const pdfFile of pdfFiles) {
                                        await sock.sendMessage(from, {
                                            document: Buffer.from(pdfFile.base64, 'base64'),
                                            mimetype: 'application/pdf',
                                            fileName: pdfFile.name,
                                            caption: pdfFile.caption || `Document pour *${identifier}*.`
                                        }, { quoted: msg });
                                    }
                                } else {
                                    // Merge multiple PDFs, handle individual failures
                                    const mergedPdf = await PDFDocument.create();
                                    let mergedCount = 0;
                                    const failedPdfs = [];

                                    for (const pdfFile of pdfFiles) {
                                        try {
                                            const pdfDoc = await PDFDocument.load(Buffer.from(pdfFile.base64, 'base64'), { ignoreEncryption: true });
                                            const copiedPages = await mergedPdf.copyPages(pdfDoc, pdfDoc.getPageIndices());
                                            copiedPages.forEach((page) => mergedPdf.addPage(page));
                                            mergedCount++;
                                        } catch (err) {
                                            console.error("Impossible de fusionner le PDF:", pdfFile.name, err.message);
                                            failedPdfs.push(pdfFile);
                                        }
                                    }

                                    if (mergedCount > 0) {
                                        try {
                                            const mergedPdfBytes = await mergedPdf.save();
                                            await sock.sendMessage(from, {
                                                document: Buffer.from(mergedPdfBytes),
                                                mimetype: 'application/pdf',
                                                fileName: `Dossier_Partiel_${identifier}.pdf`,
                                                caption: `Documents fusionnés pour *${identifier}*.`
                                            }, { quoted: msg });
                                        } catch (saveErr) {
                                            console.error("Erreur lors de la sauvegarde du PDF fusionné:", saveErr);
                                            for(const f of pdfFiles) { if (!failedPdfs.includes(f)) failedPdfs.push(f); }
                                        }
                                    }

                                    if (failedPdfs.length > 0) {
                                        await sock.sendMessage(from, { text: "⚠️ Certains documents n'ont pas pu être fusionnés (format de scan non supporté) et sont envoyés séparément ci-dessous :" }, { quoted: msg });
                                        for (const file of failedPdfs) {
                                            await sock.sendMessage(from, {
                                                document: Buffer.from(file.base64, 'base64'),
                                                mimetype: 'application/pdf',
                                                fileName: file.name,
                                                caption: file.caption || `Document pour *${identifier}*.`
                                            }, { quoted: msg });
                                        }
                                    }
                                }
                            }
                            """
    
    content = content[:start_idx] + new_block + "                            " + content[end_idx:]
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Syntax fixed")
