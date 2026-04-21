# WhatsApp Stock Kal3iya Bot

Bot WhatsApp qui répond aux questions sur le stock via l'API Odoo + OpenAI.

## Prérequis

- **Node.js** 18+ installé sur le serveur
- **Odoo** avec le module `stock_kal3iya` mis à jour
- **OpenAI API key** configurée dans Odoo
- Un **numéro WhatsApp** dédié au bot

## Installation

```bash
# 1. Aller dans le dossier du connecteur
cd custom-addons/stock_kal3iya/whatsapp-connector

# 2. Installer les dépendances
npm install whatsapp-web.js qrcode-terminal axios dotenv

# 3. Copier et remplir la configuration
cp .env.example .env
# Éditer .env avec vos valeurs
```

## Configuration Odoo

Avant de lancer le bot, configurez ces **Paramètres Système** dans Odoo
(*Configuration → Technique → Paramètres → Paramètres Système*) :

| Clé | Valeur |
|-----|--------|
| `stock_kal3iya.api_token` | Token secret pour l'API (ex: `mon_token_secret_123`) |
| `stock_kal3iya.openai_api_key` | Votre clé API OpenAI (ex: `sk-...`) |

## Lancement

```bash
node bot.js
```

1. Un **QR code** s'affiche dans le terminal
2. Ouvrez WhatsApp sur le téléphone du numéro dédié
3. Allez dans **Appareils connectés** → **Connecter un appareil**
4. Scannez le QR code
5. ✅ Le bot est prêt !

## Utilisation

Envoyez un message au numéro WhatsApp du bot :

| Message | Réponse |
|---------|---------|
| `Combien d'amande ?` | `150 colis` |
| `Stock amande garage 1` | `75 colis` |
| `Liste des produits` | Liste des produits en stock |
| `Bonjour` | Message d'aide |

## Exécution en production

Pour garder le bot actif en permanence, utilisez `pm2` :

```bash
npm install -g pm2
pm2 start bot.js --name stock-whatsapp
pm2 save
pm2 startup
```
