# Código Python principal para o bot de estoque no Telegram

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import pandas as pd
import os
import logging

# Configuração de Logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# O arquivo Excel será salvo no diretório de trabalho do Render
ARQUIVO_ESTOQUE = "estoque.xlsx"
# O token é lido de uma variável de ambiente (configurada no Render)
TOKEN = os.environ.get("BOT_TOKEN")

# --- Carrega o Excel (Função Auxiliar) ---
def carregar_estoque():
    """Tenta carregar o DataFrame do arquivo de estoque."""
    try:
        if os.path.exists(ARQUIVO_ESTOQUE):
            # Usar engine 'openpyxl' para arquivos .xlsx
            return pd.read_excel(ARQUIVO_ESTOQUE, engine="openpyxl")
    except Exception as e:
        logger.error(f"Erro ao carregar o estoque: {e}")
        return None
    return None

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /start e oferece instruções."""
    await update.message.reply_text(
        "👋 Olá! Eu sou seu Bot de Estoque.\n\n"
        "1. Para começar, envie o arquivo Excel (.xlsx) com seu estoque.\n"
        "2. Depois, use /buscar <termo> para encontrar itens."
    )

# --- /buscar ---
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca termos no arquivo de estoque atual."""
    estoque = carregar_estoque()
    if estoque is None:
        await update.message.reply_text(
            "❌ Nenhum arquivo de estoque foi encontrado. Envie um antes de usar os comandos."
        )
        return

    args = context.args
    if not args:
        await update.message.reply_text("Use assim: /buscar <texto>")
        return

    termo = " ".join(args).lower()
    
    # Busca por termo em qualquer coluna, convertendo tudo para string minúscula
    try:
        resultado = estoque[
            estoque.astype(str).apply(lambda linha: linha.str.lower().str.contains(termo, na=False).any(), axis=1)
        ]
    except Exception as e:
        logger.error(f"Erro durante a filtragem de busca: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao processar a busca.")
        return


    if resultado.empty:
        await update.message.reply_text("Nenhum resultado encontrado.")
    else:
        # Formata o resultado para exibição
        # Remove o índice para uma visualização mais limpa
        texto = resultado.to_string(index=False)
        
        # O limite de caracteres do Telegram é de 4096. Usamos 4000 por segurança.
        if len(texto) > 4000:
            texto = texto[:4000] + "\n\n⚠️ Resultado muito longo, mostrei apenas parte."
        
        await update.message.reply_text(f"📦 Resultados encontrados:\n\n{texto}")

# --- Receber novo arquivo Excel ---
async def receber_arquivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com o recebimento e salvamento do novo arquivo de estoque."""
    if update.message.document:
        doc = update.message.document

        # Verifica se o arquivo é um .xlsx
        if not doc.file_name.lower().endswith(".xlsx"):
            await update.message.reply_text("❌ Envie apenas arquivos .xlsx, por favor.")
            return

        try:
            # Baixa o arquivo
            file = await context.bot.get_file(doc.file_id)
            # Salva o arquivo com o nome ARQUIVO_ESTOQUE
            await file.download_to_drive(ARQUIVO_ESTOQUE)
            await update.message.reply_text("✅ O arquivo de estoque foi atualizado com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao baixar ou salvar arquivo: {e}")
            await update.message.reply_text(
                "❌ Ocorreu um erro ao salvar o arquivo. Tente novamente."
            )
    else:
        await update.message.reply_text("Envie o arquivo Excel (.xlsx) contendo o novo estoque.")

# --- Inicializa o bot e roda o polling ---
def main():
    """Função principal que inicia o bot."""
    if not TOKEN:
        logger.error("A variável de ambiente BOT_TOKEN não foi configurada.")
        print("ERRO: BOT_TOKEN não encontrado. Configure a variável de ambiente.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Adiciona os Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buscar", buscar))
    # Filtra apenas documentos que não são comandos (para permitir o upload do Excel)
    app.add_handler(MessageHandler(filters.Document.ALL & (~filters.COMMAND), receber_arquivo))

    logger.info("🤖 Bot rodando online (Modo Polling)...")
    
    # O modo polling é mais simples para esta configuração no Render.
    app.run_polling()


if __name__ == "__main__":
    main()
