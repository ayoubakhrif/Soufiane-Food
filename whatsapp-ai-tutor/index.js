require('dotenv').config();
const { makeWASocket, useMultiFileAuthState, DisconnectReason, getContentType, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const pino = require('pino');

const GROUP_ID = "120363427130703615@g.us";
const EXPERT_ID = "212716293509@s.whatsapp.net";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
    console.error("Veuillez définir OPENAI_API_KEY dans le fichier .env");
    process.exit(1);
}

// Mémoire pour stocker les questions envoyées à l'expert
// Clé: ID du message envoyé à l'expert, Valeur: { originalMsg, originalText }
const pendingQuestions = new Map();

// System prompt principal (pour juger et répondre directement)
const SYSTEM_PROMPT = `Tu es un tuteur expert en Intelligence Artificielle.
Tu fais partie d'un groupe WhatsApp avec tes stagiaires et leur encadrant.
Ton rôle est de répondre à toutes leurs questions sur l'IA.
Tu peux répondre en arabe ou en français, selon la langue utilisée dans la question.

RÈGLES ABSOLUES :
1. Tes réponses doivent être très COURTES et concises.
2. Tu dois te comporter exactement comme un être humain (un vrai tuteur). Ne dis JAMAIS que tu es une intelligence artificielle, un bot, un modèle de langage, etc. Garde un ton naturel et humain.
3. Si tu ne connais pas la réponse avec certitude, ou si c'est une question très spécifique que tu ne peux pas résoudre seul, tu dois l'indiquer.

Tu DOIS répondre au format JSON strict avec la structure suivante :
{
  "connait_reponse": true ou false,
  "reponse_directe": "Ta réponse courte et naturelle (si tu connais la réponse). Laisse vide si false.",
  "question_formulee": "La question exacte posée par l'utilisateur (si tu ne connais pas la réponse, pour qu'on puisse la demander à un expert)"
}`;

let sock;

async function connectToWhatsApp() {
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`Utilisation de WA v${version.join('.')} (Latest: ${isLatest})`);

    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');

    sock = makeWASocket({
        version,
        auth: state,
        logger: pino({ level: 'silent' }),
        browser: ['AI Tutor', 'Chrome', '1.0.0'],
        syncFullHistory: false,
        generateHighQualityLinkPreview: true
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('\n--- SCANNEZ LE QR CODE AVEC WHATSAPP ---');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = (lastDisconnect.error instanceof Boom) ?
                lastDisconnect.error.output.statusCode : 0;

            console.log(`Connexion fermée (Code: ${statusCode}). Reconnexion en cours...`);
            if (statusCode !== DisconnectReason.loggedOut) {
                setTimeout(connectToWhatsApp, 5000);
            } else {
                console.log('Déconnecté. Supprimez le dossier "auth_info_baileys" et relancez.');
            }
        } else if (connection === 'open') {
            console.log('✅ Connecté à WhatsApp ! Le tuteur est prêt.');
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;

        for (const msg of m.messages) {
            if (!msg.message || msg.key.fromMe) continue;

            const from = msg.key.remoteJid;
            
            let text = (getContentType(msg.message) === 'conversation') ? msg.message.conversation :
                (getContentType(msg.message) === 'extendedTextMessage') ? msg.message.extendedTextMessage.text : '';

            if (!text) continue;

            // -------------------------------------------------------------
            // CAS 1: Message de l'Expert (Réponse à une question transférée)
            // -------------------------------------------------------------
            if (from === EXPERT_ID) {
                // Vérifier s'il répond à un message précis
                const contextInfo = msg.message.extendedTextMessage?.contextInfo;
                if (contextInfo && contextInfo.stanzaId) {
                    const repliedMsgId = contextInfo.stanzaId;
                    
                    if (pendingQuestions.has(repliedMsgId)) {
                        console.log(`\n💡 Réponse de l'expert reçue: "${text}"`);
                        
                        const { originalMsg, originalText } = pendingQuestions.get(repliedMsgId);
                        
                        try {
                            await sock.sendPresenceUpdate('composing', GROUP_ID);

                            // On demande à l'IA de reformuler la réponse de l'expert
                            const rewritePrompt = `Tu es le tuteur humain du groupe. Un stagiaire avait posé cette question : "${originalText}".\nTu avais dit que tu allais vérifier.\nVoici l'information brute trouvée : "${text}".\nReformule cette réponse pour le groupe de manière COURTE, très naturelle et humaine. Ne dis pas "l'expert a dit", agis comme si c'était toi qui avais trouvé la réponse.`;
                            
                            const rewriteResponse = await axios.post('https://api.openai.com/v1/chat/completions', {
                                model: "gpt-4o",
                                messages: [{ role: "user", content: rewritePrompt }],
                                temperature: 0.7,
                                max_tokens: 400
                            }, {
                                headers: {
                                    'Authorization': `Bearer ${OPENAI_API_KEY}`,
                                    'Content-Type': 'application/json'
                                }
                            });

                            const finalReply = rewriteResponse.data.choices[0].message.content;
                            console.log(`🤖 Réponse reformulée pour le groupe : "${finalReply}"`);

                            // Envoi au groupe (en citant la question originale)
                            await sock.sendMessage(GROUP_ID, { text: finalReply }, { quoted: originalMsg });
                            await sock.sendPresenceUpdate('paused', GROUP_ID);
                            
                            // On nettoie la mémoire
                            pendingQuestions.delete(repliedMsgId);
                        } catch (error) {
                            console.error("Erreur lors de la reformulation :", error.message);
                        }
                    }
                }
                continue; // On ne traite pas les autres messages de l'expert comme des questions de stagiaire
            }

            // -------------------------------------------------------------
            // CAS 2: Message dans le groupe
            // -------------------------------------------------------------
            if (from !== GROUP_ID) continue;

            console.log(`\n💬 Message du groupe : "${text}"`);
            
            try {
                await sock.sendPresenceUpdate('composing', from);

                // Appel à l'API OpenAI avec JSON mode
                const response = await axios.post('https://api.openai.com/v1/chat/completions', {
                    model: "gpt-4o",
                    response_format: { type: "json_object" },
                    messages: [
                        { role: "system", content: SYSTEM_PROMPT },
                        { role: "user", content: text }
                    ],
                    temperature: 0.7,
                    max_tokens: 800
                }, {
                    headers: {
                        'Authorization': `Bearer ${OPENAI_API_KEY}`,
                        'Content-Type': 'application/json'
                    }
                });

                const aiReplyRaw = response.data.choices[0].message.content;
                const aiResult = JSON.parse(aiReplyRaw);

                if (aiResult.connait_reponse) {
                    console.log(`🤖 Réponse IA directe : "${aiResult.reponse_directe}"`);
                    await sock.sendMessage(from, { text: aiResult.reponse_directe }, { quoted: msg });
                } else {
                    console.log(`⚠️ L'IA ne sait pas. Transfert à l'expert.`);
                    // 1. Dire au groupe de patienter
                    await sock.sendMessage(from, { text: "Je vais vérifier et vous répondre" }, { quoted: msg });
                    
                    // 2. Transférer à l'expert
                    const expertMsgText = `❓ Question posée dans le groupe AI:\n"${text}"\n\nMerci de répondre à CE message pour que je puisse transférer ta réponse au groupe.`;
                    const sentToExpertMsg = await sock.sendMessage(EXPERT_ID, { text: expertMsgText });
                    
                    // 3. Enregistrer l'ID pour faire le lien plus tard
                    pendingQuestions.set(sentToExpertMsg.key.id, {
                        originalMsg: msg,
                        originalText: text
                    });
                }
                
                await sock.sendPresenceUpdate('paused', from);

            } catch (error) {
                console.error("Erreur lors de l'appel à l'API OpenAI :", error.response ? error.response.data : error.message);
            }
        }
    });
}

connectToWhatsApp();
