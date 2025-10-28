import os
import pandas as pd
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.ext._utils.types import BD
from telegram.ext import ApplicationBuilder

# === Configuração básica ===
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))  # Render define automaticamente
ARQUIVO_ESTOQUE = "estoque.xlsx"

app_flask = Flask(__name__)
bot_app: Application = None

# === Funções de estoque ===
def carregar_estoque():
    if os.path.exists(ARQUIVO_ESTOQUE):
        return pd.read_excel(ARQUIVO_ESTOQUE, engine="openpyxl")
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou o bot de estoque.\n"
        "Envie um arquivo Excel (.xlsx) e use /buscar <termo> para consultar."
    )

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estoque = carregar_estoque()
    if estoque is None:
        await update.message.reply_text("❌ Nenhum arquivo de estoque foi encontrado.")
        return

    termo = " ".join(context.args).lower() if context.args else ""
    if not termo:
        await update.message.reply_text("Use assim: /buscar <texto>")
        return

    colunas_busca = [c for c in estoque.columns if str(c).lower() != "quantidade"]
    filtrado = estoque[
        estoque[colunas_busca].astype(str).apply(lambda row: row.str.lower().str.contains(termo).any(), axis=1)
    ]

    if filtrado.empty:
        await update.message.reply_text("Nenhum resultado encontrado.")
    else:
        texto = filtrado.to_string(index=False)
        if len(texto) > 4000:
            texto = texto[:4000] + "\n\n⚠️ Resultado muito longo, mostrado parcialmente."
        await update.message.reply_text(f"📦 Resultados encontrados:\n\n{texto}")

async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        doc = update.message.document
        if not doc.file_name.endswith(".xlsx"):
            await update.message.reply_text("❌ Envie apenas arquivos .xlsx, por favor.")
            return
        file = await context.bot.get_file(doc.file_id)
        await file.download_to_drive(ARQUIVO_ESTOQUE)
        await update.message.reply_text("✅ Arquivo de estoque atualizado com sucesso!")

# === Inicialização do bot ===
async def iniciar_bot():
    global bot_app
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("buscar", buscar))
    bot_app.add_handler(MessageHandler(filters.Document.ALL & (~filters.COMMAND), receber_arquivo))
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()  # só para inicializar handlers

# === Rota Webhook ===
@app_flask.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK", 200

@app_flask.route("/", methods=["GET"])
def home():
    return "🤖 Bot de Estoque rodando via Webhook!", 200

# === Inicialização ===
if __name__ == "__main__":
    import asyncio
    asyncio.run(iniciar_bot())
    app_flask.run(host="0.0.0.0", port=PORT)
