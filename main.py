# main.py - Telegram stock bot for Render
# Searches columns: Endereço, UA, Produto, Descrição (Quantidade is displayed but NOT used for search)
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pandas as pd

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ARQUIVO_ESTOQUE = "estoque.xlsx"  # file saved in app working directory
TOKEN = os.environ.get("BOT_TOKEN")  # read token from Render environment variables

# Helper: load excel if exists
def carregar_estoque():
    try:
        if os.path.exists(ARQUIVO_ESTOQUE):
            # force openpyxl engine for .xlsx
            df = pd.read_excel(ARQUIVO_ESTOQUE, engine="openpyxl")
            # Normalize columns (strip spaces)
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception as e:
        logger.error(f"Erro ao carregar o estoque: {e}")
        return None
    return None

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou seu Bot de Estoque.\n\n"
        "1) Envie o arquivo Excel (.xlsx) com seu estoque (colunas: Endereço, UA, Produto, Descrição, Quantidade).\n"
        "2) Use /buscar <termo> para procurar nas colunas Endereço, UA, Produto e Descrição.\n\n"
        "Exemplo: /buscar parafuso\n\n"
        "Observação: A coluna 'Quantidade' é apenas exibida, não utilizada como filtro."
    )

# /buscar command - searches only in selected columns (not Quantidade)
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = carregar_estoque()
    if df is None:
        await update.message.reply_text("❌ Nenhum arquivo de estoque foi encontrado. Envie um .xlsx para começar.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Use assim: /buscar <termo>")
        return

    termo = " ".join(args).lower()

    # Columns to search (prefer user-specified names) - fallback to any string columns except Quantidade
    preferred = ["Endereço", "UA", "Produto", "Descrição"]
    available = [c for c in preferred if c in df.columns]
    if not available:
        # fallback to searching all columns except 'Quantidade' if preferred headers not found
        available = [c for c in df.columns if str(c).strip().lower() != "quantidade"]

    try:
        mask_rows = df[available].astype(str).apply(lambda col: col.str.lower().str.contains(termo, na=False))
        # any column match per row
        matched = df[mask_rows.any(axis=1)]
    except Exception as e:
        logger.error(f"Erro na filtragem: {e}")
        await update.message.reply_text("❌ Erro ao processar a busca. Verifique o arquivo e tente novamente.")
        return

    if matched.empty:
        await update.message.reply_text("Nenhum resultado encontrado.")
        return

    texto = matched.to_string(index=False)
    if len(texto) > 4000:
        texto = texto[:4000] + "\n\n⚠️ Resultado muito longo, mostrei apenas parte."
    await update.message.reply_text(f"📦 Resultados encontrados:\n\n{texto}")

# receive uploaded .xlsx and replace inventory file
async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        doc = update.message.document
        name = doc.file_name or ""
        if not name.lower().endswith(".xlsx"):
            await update.message.reply_text("❌ Envie apenas arquivos .xlsx, por favor.")
            return
        try:
            file = await context.bot.get_file(doc.file_id)
            await file.download_to_drive(ARQUIVO_ESTOQUE)
            await update.message.reply_text("✅ O arquivo de estoque foi atualizado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao baixar/salvar arquivo: {e}")
            await update.message.reply_text("❌ Falha ao salvar o arquivo. Tente novamente.")
    else:
        await update.message.reply_text("Envie o arquivo Excel (.xlsx) contendo o novo estoque.")

def main():
    if not TOKEN:
        logger.error("BOT_TOKEN não configurado. Defina a variável de ambiente BOT_TOKEN no Render.")
        print("ERRO: BOT_TOKEN não encontrado.")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(MessageHandler(filters.Document.ALL & (~filters.COMMAND), receber_arquivo))

    logger.info("🤖 Bot iniciado (polling).")
    app.run_polling()

if __name__ == "__main__":
    main()
