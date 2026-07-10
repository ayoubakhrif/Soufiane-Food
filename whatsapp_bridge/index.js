const {
    makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    getContentType,
    fetchLatestBaileysVersion,
    downloadMediaMessage
} = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const fs = require('fs');
const pino = require('pino');
const express = require('express');
const { PDFDocument } = require('pdf-lib');


// CONFIGURATION
const ARTICLE_GROUP_ID = "120363405648854156@g.us";
const CLIENT_GROUP_ID = "120363426234155722@g.us";
const STOCK_VALIDATION_GROUP_ID = "120363403203705514@g.us";
const FINANCE_GROUP_ID = "120363428965532100@g.us";
const LOGISTICS_GROUP_ID = "120363427755410654@g.us";
const LOGISTICS_PAYMENT_GROUP_ID = "120363407897068761@g.us";
const DOUANE_GROUP_ID = "120363406635335778@g.us";
const SORTIE_GROUP_ID = "120363424919316319@g.us";
const CASA_CORRECTION_GROUP_ID = "120363049891261462@g.us";
const PRICE_GROUP_ID = "120363428923348892@g.us";
const FINANCE_PDF_GROUP_ID = "120363426857783962@g.us";
const DOSSIER_VERIF_GROUP_ID = "120363408433779149@g.us";
const DOSSIER_SEARCH_GROUP_ID = "120363425063313711@g.us";
const LOGISTICS_PDF_GROUP_ID = "120363428159815503@g.us";
const TRANSPORT_GROUP_ID = "120363409412071351@g.us";
const SURESTARIE_REPORT_GROUP_ID = "120363410175900080@g.us";
const TRESORERIE_CHQ_GROUP_ID = "120363427689661439@g.us";

const ARTICLE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/stock?db=soufianefoods";
const CLIENT_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/client?db=soufianefoods";
const SURESTARIE_REPORT_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/surestarie_report?db=soufianefoods";
const STOCK_VALIDATION_ODOO_URL = "https://gestia-soufianefoods.cloud/api/stock_kal3iya/chat";
const FINANCE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/finance?db=soufianefoods";
const LOGISTICS_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/logistics?db=soufianefoods";
const LOGISTICS_PAYMENT_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/logistics_payment?db=soufianefoods";
const DOUANE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/douane?db=soufianefoods";
const SORTIE_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/sortie?db=soufianefoods";
const CASA_CORRECTION_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/casa_correction?db=soufianefoods";
const FINANCE_PDF_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/finance/pdf?db=soufianefoods";
const DOSSIER_VERIF_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/dossier_verification?db=soufianefoods";
const DOSSIER_SEARCH_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/dossier_search?db=soufianefoods";
const LOGISTICS_PDF_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/logistique/pdf?db=soufianefoods";
const TRANSPORT_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/transport?db=soufianefoods";
const TRESORERIE_CHQ_ODOO_URL = "https://gestia-soufianefoods.cloud/api/whatsapp/tresorerie_chq/pdf?db=soufianefoods";

const API_KEY = "whatsapp_direct_quantity"; // À définir dans Odoo (Paramètres système)

let odooSessionCookie = '';
const pendingChoices = new Map(); // Garde en mémoire les menus interactifs par groupe
const dossierVerifBuffer = []; // Buffer for dossier verification docs

let sock; // Global socket variable

async function connectToWhatsApp() {
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`Utilisation de la version WA v${version.join('.')} (Est la plus récente : ${isLatest})`);

    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');

    sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'debug' }),
        browser: ['Gestia Bot', 'Chrome', '114.0.5735.199'], // Version de Chrome fixe
        syncFullHistory: false, // Évite la synchronisation lourde au début
        generateHighQualityLinkPreview: true
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('--- SCANNEZ LE QR CODE CI-DESSOUS ---');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = (lastDisconnect.error instanceof Boom) ?
                lastDisconnect.error.output.statusCode : 0;

            console.log(`Connexion fermée (Code: ${statusCode})...`);

            if (statusCode !== DisconnectReason.loggedOut) {
                console.log('Reconnexion en cours...');
                setTimeout(() => connectToWhatsApp(), 5000); // Attendre 5s avant de retenter
            } else {
                console.log('Déconnexion effectuée. Supprimez le dossier "auth_info_baileys" pour recommencer.');
            }
        } else if (connection === 'open') {
            console.log('--- CONNEXION WHATSAPP ÉTABLIE ---');
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;

        for (const msg of m.messages) {
            if (!msg.message || msg.key.fromMe) continue;

            const from = msg.key.remoteJid;
            let text = (getContentType(msg.message) === 'conversation') ? msg.message.conversation :
                (getContentType(msg.message) === 'extendedTextMessage') ? msg.message.extendedTextMessage.text : 
                (getContentType(msg.message) === 'documentWithCaptionMessage') ? msg.message.documentWithCaptionMessage.message.documentMessage.caption : '';

            const isDocument = !!(msg.message.documentMessage || msg.message.documentWithCaptionMessage);

            if (!text && !isDocument) continue;

            console.log(`Message de ${from} : "${text}"`);
            let realMessage = text;

            // DETERMINATION DU TYPE DE REQUÊTE SELON LE GROUPE
            let targetOdooUrl = "";
            let isClientRequest = false;

            if (from === ARTICLE_GROUP_ID) {
                targetOdooUrl = ARTICLE_ODOO_URL;
                isClientRequest = false;
            } else if (from === CLIENT_GROUP_ID) {
                targetOdooUrl = CLIENT_ODOO_URL;
                isClientRequest = true;
            } else if (from === STOCK_VALIDATION_GROUP_ID) {
                targetOdooUrl = STOCK_VALIDATION_ODOO_URL;
                isClientRequest = false;
            } else if (from === FINANCE_GROUP_ID) {
                targetOdooUrl = FINANCE_ODOO_URL;
                isClientRequest = true; // Use true to reuse the identifier/caption logic in bridge
            } else if (from === LOGISTICS_GROUP_ID) {
                targetOdooUrl = LOGISTICS_ODOO_URL;
                isClientRequest = false;
            } else if (from === LOGISTICS_PAYMENT_GROUP_ID) {
                targetOdooUrl = LOGISTICS_PAYMENT_ODOO_URL;
                isClientRequest = false;
            } else if (from === DOUANE_GROUP_ID) {
                targetOdooUrl = DOUANE_ODOO_URL;
                isClientRequest = false;
            } else if (from === SORTIE_GROUP_ID) {
                targetOdooUrl = SORTIE_ODOO_URL;
                isClientRequest = false;
            } else if (from === FINANCE_PDF_GROUP_ID) {
                targetOdooUrl = FINANCE_PDF_ODOO_URL;
                isClientRequest = false;
            } else if (from === LOGISTICS_PDF_GROUP_ID) {
                targetOdooUrl = LOGISTICS_PDF_ODOO_URL;
                isClientRequest = false;
            } else if (from === DOSSIER_SEARCH_GROUP_ID) {
                targetOdooUrl = DOSSIER_SEARCH_ODOO_URL;
                isClientRequest = false;
            } else if (from === DOSSIER_VERIF_GROUP_ID) {
                targetOdooUrl = DOSSIER_VERIF_ODOO_URL;
                isClientRequest = false;
                
                if (isDocument) {
                    try {
                        const buffer = await downloadMediaMessage(
                            msg,
                            'buffer',
                            { },
                            { logger: pino({ level: 'silent' }), reuploadRequest: sock.updateMediaMessage }
                        );
                        const docMsg = msg.message.documentMessage || msg.message.documentWithCaptionMessage?.message?.documentMessage;
                        const fileName = docMsg?.fileName || 'document.pdf';
                        dossierVerifBuffer.push({
                            pdf_base64: buffer.toString('base64'),
                            file_name: fileName,
                            message_key: msg.key
                        });
                        console.log(`Document ${fileName} mis en file d'attente pour vérification.`);
                    } catch (err) {
                        console.error("Erreur téléchargement document:", err);
                    }
                    continue; // Do not call Odoo yet
                } else if (realMessage && (realMessage.includes("➖➖➖➖➖➖➖➖➖➖➖") || realMessage.includes("----------"))) {
                    if (dossierVerifBuffer.length === 0) {
                        console.log("Série de tirets reçue mais aucun document en file d'attente.");
                        continue;
                    }
                    console.log(`Lancement de la vérification pour ${dossierVerifBuffer.length} documents.`);
                } else {
                    continue; // Ignore other texts in this group
                }
            } else if (from === TRANSPORT_GROUP_ID) {
                targetOdooUrl = TRANSPORT_ODOO_URL;
                isClientRequest = false;
            } else if (from === SURESTARIE_REPORT_GROUP_ID) {
                targetOdooUrl = SURESTARIE_REPORT_ODOO_URL;
                isClientRequest = false;
            } else if (from === TRESORERIE_CHQ_GROUP_ID) {
                targetOdooUrl = TRESORERIE_CHQ_ODOO_URL;
                isClientRequest = false;
            } else {
                console.log(`Ignoré (destinataire ${from} non autorisé)`);
                continue;
            }

            // GESTION DU MENU INTERACTIF
            const quotedMsgId = msg.message?.extendedTextMessage?.contextInfo?.stanzaId;
            let choices = null;
            let usedKey = null;

            if (quotedMsgId && pendingChoices.has(quotedMsgId)) {
                choices = pendingChoices.get(quotedMsgId);
                usedKey = quotedMsgId;
            } else if (pendingChoices.has(from)) {
                choices = pendingChoices.get(from);
                usedKey = from;
            }

            if (choices) {
                const trimmedText = text.trim();
                
                const parts = trimmedText.split(/[\s,-]+/).filter(p => p);
                let allValid = true;
                const selectedChoices = [];
                
                for (const part of parts) {
                    const choiceNum = parseInt(part);
                    if (isNaN(choiceNum) || choiceNum <= 0 || choiceNum > choices.length) {
                        allValid = false;
                        break;
                    }
                    selectedChoices.push(choices[choiceNum - 1]);
                }

                if (parts.length > 0 && allValid) {
                    realMessage = selectedChoices.join('|');
                    console.log(`Sélection utilisateur multiple (clé: ${usedKey}) : ${trimmedText} -> "${realMessage}"`);
                    if (usedKey === from) pendingChoices.delete(from); // Clear fallback, but keep quoted msg IDs active
                }
                else if (parts.length > 0 && !allValid && parts.every(p => !isNaN(parseInt(p)) && p.length <= 2)) {
                    await sock.sendMessage(from, { text: "⚠️ Choix invalide. Veuillez répondre par un ou plusieurs numéros valides (ex: 1 3 5)." }, { quoted: msg });
                    continue; // Skip Odoo call
                }
                else {
                    console.log(`Menu abandonné pour une nouvelle saisie : "${trimmedText}"`);
                    if (usedKey === from) pendingChoices.delete(from);
                }
            }

            try {
                // AUTHENTIFICATION ODOO (pour contourner le DB Proxy 404)
                if (!odooSessionCookie) {
                    console.log("Demande de session (Cookie) à Odoo...");
                    const authRes = await axios.post("https://gestia-soufianefoods.cloud/web/session/authenticate", {
                        jsonrpc: "2.0",
                        params: {
                            db: "soufianefoods",
                            login: "ai_whatsapp_bot@soufianefoods.com",
                            password: "0000"
                        }
                    });
                    if (authRes.headers['set-cookie']) {
                        odooSessionCookie = authRes.headers['set-cookie'].find(c => c.startsWith('session_id='));
                        console.log("Session Odoo activée.");
                    } else {
                        console.log("Impossible d'obtenir la session Odoo.");
                    }
                }

                // APPEL À ODOO
                let typeStr = "ARTICLE";
                if (from === STOCK_VALIDATION_GROUP_ID) typeStr = "STOCK_VAL";
                else if (from === CLIENT_GROUP_ID) typeStr = "CLIENT";
                else if (from === FINANCE_GROUP_ID) typeStr = "FINANCE";
                else if (from === LOGISTICS_GROUP_ID) typeStr = "LOGISTICS";
                else if (from === LOGISTICS_PAYMENT_GROUP_ID) typeStr = "LOG_PAYMENT";
                else if (from === DOUANE_GROUP_ID) typeStr = "DOUANE";
                else if (from === CASA_CORRECTION_GROUP_ID) typeStr = "CASA_CORR";
                else if (from === FINANCE_PDF_GROUP_ID) typeStr = "FINANCE_PDF";
                else if (from === LOGISTICS_PDF_GROUP_ID) typeStr = "LOGISTICS_PDF";
                else if (from === DOSSIER_VERIF_GROUP_ID) typeStr = "DOSSIER_VERIF";
                else if (from === TRANSPORT_GROUP_ID) typeStr = "TRANSPORT";
                else if (from === TRESORERIE_CHQ_GROUP_ID) typeStr = "TRESORERIE_CHQ";

                console.log(`Appel à Odoo (${typeStr}) pour : "${realMessage}"`);
                
                const requestParams = {
                    message: realMessage,
                    sender: from, // Used by stock_kal3iya
                    group_id: from // Used by others
                };

                if (from === DOSSIER_VERIF_GROUP_ID) {
                    requestParams.documents = [...dossierVerifBuffer];
                    dossierVerifBuffer.length = 0; // Clear the buffer
                }

                // Si c'est un PDF pour le bot finance, logistique, ou trésorerie, on le télécharge
                if ((from === FINANCE_PDF_GROUP_ID || from === LOGISTICS_PDF_GROUP_ID || from === TRESORERIE_CHQ_GROUP_ID) && isDocument) {
                    try {
                        console.log("Téléchargement du document PDF...");
                        const buffer = await downloadMediaMessage(
                            msg,
                            'buffer',
                            { },
                            { logger: pino({ level: 'silent' }), reuploadRequest: sock.updateMediaMessage }
                        );
                        requestParams.pdf_base64 = buffer.toString('base64');
                        
                        const docMsg = msg.message.documentMessage || msg.message.documentWithCaptionMessage?.message?.documentMessage;
                        requestParams.file_name = docMsg?.fileName || 'document.pdf';
                        console.log(`Fichier ${requestParams.file_name} prêt à être envoyé à Odoo.`);
                    } catch (err) {
                        console.error("Erreur de téléchargement du media:", err);
                    }
                }

                const response = await axios.post(targetOdooUrl, {
                    jsonrpc: "2.0",
                    params: requestParams
                }, {
                    headers: {
                        'X-Api-Key': API_KEY,
                        'Content-Type': 'application/json',
                        'Cookie': odooSessionCookie || ''
                    }
                });

                if (response.data.error) {
                    console.error("Erreur Odoo (JSON-RPC) :", JSON.stringify(response.data.error, null, 2));
                    return;
                }

                const result = response.data.result;
                console.log("Résultat Odoo :", result ? result.status : "AUCUN RESULTAT", result ? (result.message || "") : "");

                if (result && result.status === 'multiple_choices') {
                    // C'est un menu de sélection
                    pendingChoices.set(from, result.choices); // Fallback classique
                    const sentMsg = await sock.sendMessage(from, { text: result.message }, { quoted: msg });
                    if (sentMsg && sentMsg.key && sentMsg.key.id) {
                        pendingChoices.set(sentMsg.key.id, result.choices); // Sauvegarde par ID du message menu
                    }
                } else if (from === DOSSIER_VERIF_GROUP_ID && result && result.status === 'success' && result.reports) {
                    console.log(`Envoi de ${result.reports.length} rapports au groupe...`);
                    let fullReportText = "📄 *RAPPORT DE VÉRIFICATION DES DOSSIERS*\n━━━━━━━━━━━━━━━━━━\n\n";
                    for (const report of result.reports) {
                        fullReportText += report.text + "\n\n";
                    }
                    if (result.reports.length > 0) {
                        try {
                            await sock.sendMessage(from, { text: fullReportText.trim() });
                        } catch (err) {
                            console.error("Erreur envoi rapport global:", err);
                        }
                    }
                }
                else {
                    let hasAction = false;
                    
                    if (result && result.response) {
                        // C'est une réponse textuelle
                        console.log(`Réponse textuelle : ${result.response}`);
                        await sock.sendMessage(from, { text: result.response }, { quoted: msg });
                        hasAction = true;
                    }
                    
                    if (result && result.status === 'success') {
                        // Extract identifier
                        const identifier = result.client_name || result.product_name || "Bénéficiaire";
                        
                        let reportType = "de stock";
                        if (from === CLIENT_GROUP_ID) reportType = "de compte";
                        if (from === FINANCE_GROUP_ID) reportType = "financier";
                        if (from === DOUANE_GROUP_ID) reportType = "douane (DUM)";
                        if (from === SORTIE_GROUP_ID) reportType = "de sorties";
                        if (from === LOGISTICS_GROUP_ID) reportType = "logistique";
                        if (from === TRANSPORT_GROUP_ID) reportType = "chauffeur";
                        if (from === SURESTARIE_REPORT_GROUP_ID) reportType = "comparatif Surestarie/Magasinage";

                        console.log(`Entité identifiée : ${identifier}. Envoi du/des PDF(s)...`);

                        // Support for multiple files
                        if (result.files && Array.isArray(result.files)) {
                            const pdfFiles = [];
                            const nonPdfFiles = [];

                            for (const file of result.files) {
                                const base64Data = file.pdf_base64 || file.base64;
                                if (!base64Data) continue;
                                
                                let mimeType = file.mimetype;
                                if (!mimeType) {
                                    if (file.file_name.endsWith('.xlsx')) {
                                        mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
                                    } else if (file.file_name.endsWith('.xls')) {
                                        mimeType = 'application/vnd.ms-excel';
                                    } else {
                                        mimeType = 'application/pdf';
                                    }
                                }
                                
                                if (mimeType === 'application/pdf' || file.file_name.endsWith('.pdf')) {
                                    pdfFiles.push({ base64: base64Data, name: file.file_name });
                                } else {
                                    nonPdfFiles.push({ base64: base64Data, mimeType, name: file.file_name, caption: file.caption });
                                }
                            }

                            // 1. Merge and send PDFs if any
                            if (pdfFiles.length > 0) {
                                if (pdfFiles.length === 1) {
                                    await sock.sendMessage(from, {
                                        document: Buffer.from(pdfFiles[0].base64, 'base64'),
                                        mimetype: 'application/pdf',
                                        fileName: pdfFiles[0].name,
                                        caption: `Document pour *${identifier}*.`
                                    }, { quoted: msg });
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
                                            // En cas d'erreur fatale de sauvegarde, on renvoie tout en failed
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
                                                caption: `Document séparé pour *${identifier}*.`
                                            }, { quoted: msg });
                                        }
                                    }
                                }
                            }

                            // 2. Send non-PDF files separately
                            for (const file of nonPdfFiles) {
                                await sock.sendMessage(from, {
                                    document: Buffer.from(file.base64, 'base64'),
                                    mimetype: file.mimeType,
                                    fileName: file.name,
                                    caption: file.caption || `Document pour *${identifier}*.`
                                }, { quoted: msg });
                            }
                        } else if (result.pdf_base64) {
                            // Original single file support
                            await sock.sendMessage(from, {
                                document: Buffer.from(result.pdf_base64, 'base64'),
                                mimetype: 'application/pdf',
                                fileName: result.file_name,
                                caption: result.message || `Voici le rapport ${reportType} pour *${identifier}*.`
                            }, { quoted: msg });
                        } else if (from === TRESORERIE_CHQ_GROUP_ID && result.message) {
                            // Fallback for TRESORERIE_CHQ_GROUP_ID
                            await sock.sendMessage(from, { text: result.message }, { quoted: msg });
                        }
                        hasAction = true;
                    }
                    
                    if (result && result.status === 'not_found') {
                        console.log(`Non trouvé : ${result.message}`);
                        await sock.sendMessage(from, { text: result.message }, { quoted: msg });
                        hasAction = true;
                    } else if (result && result.status === 'ignored') {
                        // Silently ignore as requested (noise filtering)
                        console.log(`Action : Message ignoré (bruit détecté)`);
                        hasAction = true;
                    }
                    
                    if (!hasAction && result) {
                        console.log("Structure de réponse inattendue :", JSON.stringify(response.data, null, 2));
                    }
                }

            } catch (error) {
                console.error("Erreur d'appel Odoo :", error.message);
                if (error.response) {
                    console.error("Status Erreur :", error.response.status);
                    console.error("Data Erreur :", error.response.data);
                    
                    // Si le proxy Odoo retourne une 404 ou 401, il se peut que la session ait expiré.
                    // On vide le cookie pour forcer une reconnexion au prochain message.
                    if (error.response.status === 404 || error.response.status === 401) {
                        console.log("Session Odoo potentiellement expirée (404/401). Nettoyage du cookie...");
                        odooSessionCookie = '';
                    }
                }
            }
        }
    });
}

// EXPRESS SERVER FOR PROACTIVE MESSAGES (Started once)
const app = express();
app.use(express.json({ limit: '10mb' }));

app.post('/api/send', async (req, res) => {
    const { group_id, text, document, fileName } = req.body;
    if (!group_id || !text) {
        return res.status(400).json({ status: 'error', message: 'Missing group_id or text' });
    }

    if (!sock) {
        console.log(`[BOT] Tentative d'envoi mais socket non initialisé.`);
        return res.status(503).json({ status: 'error', message: 'WhatsApp socket not initialized' });
    }

    try {
        console.log(`[BOT] Reçu demande d'envoi pour ${group_id}...`);
        await sock.sendMessage(group_id, { text });
        console.log(`[BOT] Message envoyé avec succès à ${group_id}`);
        res.json({ status: 'success' });
    } catch (err) {
        console.error(`[BOT] ÉCHEC envoi message :`, err.message);
        res.status(500).json({ status: 'error', message: err.message });
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`--- BRIDGE API ÉCOUTE SUR LE PORT ${PORT} ---`);
});

connectToWhatsApp();
