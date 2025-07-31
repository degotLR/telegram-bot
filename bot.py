from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask
import threading
import os
import time
import json

# --- Servidor Flask (para Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot activo y funcionando correctamente."

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- Configuración del bot ---
# Archivo donde se guardan los correos
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6605787552

solicitudes_pendientes = {}

CORREOS_AUTORIZADOS_FILE = 'correos_autorizados.txt'  # <--- CAMBIO: ahora usamos .txt

# 🔄 Guardar correos en .txt
def guardar_correos_autorizados(correos):
    with open(CORREOS_AUTORIZADOS_FILE, 'w') as f:
        for correo in correos:
            f.write(correo + '\n')

# 🔄 Cargar correos desde .txt
def cargar_correos_autorizados():
    try:
        with open(CORREOS_AUTORIZADOS_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

correos_autorizados = cargar_correos_autorizados()

# --- Funciones del bot ---
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        args = context.args

        if not args:
            await update.message.reply_text("❗ Usa el comando así: /buscar correo@ejemplo.com")
            return

        correo = args[0].lower()

        if correo not in correos_autorizados:
            await update.message.reply_text("❌ Ese correo no está autorizado.")
            return

        solicitudes_pendientes[user.id] = correo

        botones = [
            [InlineKeyboardButton("🏖️ Estoy de viaje", callback_data='viaje')],
            [InlineKeyboardButton("🏠 Actualizar hogar", callback_data='hogar')],
            [InlineKeyboardButton("🔐 Cambiar contraseña", callback_data='cambiar')],
            [InlineKeyboardButton("📧 Código de inicio", callback_data='codigo')]
        ]
        teclado = InlineKeyboardMarkup(botones)

        await update.message.reply_text(
            "🔎 Correo validado ✅\nAhora elige la opción:",
            reply_markup=teclado
        )

    except Exception as e:
        print(f"❌ Error en /buscar: {e}")
        await update.message.reply_text("⚠️ Error interno. Intenta más tarde.")

async def opcion_elegida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        opcion = query.data
        correo = solicitudes_pendientes.get(user_id, "No registrado")

        opciones_texto = {
            "viaje": "Estoy de viaje",
            "hogar": "Actualizar hogar",
            "cambiar": "Cambiar contraseña",
            "codigo": "Código de inicio de sesión"
        }

        texto_opcion = opciones_texto.get(opcion, opcion)

        await query.edit_message_text("🔍 Buscando datos... Por favor espera... Tiempo estimado (30-60 seg)...")

        bot = Bot(token=TOKEN)
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📩 Solicitud recibida:\n"
                f"👤 Usuario: @{query.from_user.username} (ID: {user_id})\n"
                f"📧 Correo: {correo}\n"
                f"🛠️ Opción elegida: {texto_opcion}"
            )
        )

    except Exception as e:
        print(f"❌ Error en opción_elegida: {e}")

async def enviar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text("❌ No tienes permiso para usar este comando.")
            return

        args = context.args
        if len(args) < 2:
            await update.message.reply_text("❗ Usa el comando así: /enviar ID_USUARIO datos_a_enviar")
            return

        user_id = int(args[0])
        datos = ' '.join(args[1:])
        tipo_dato = "enlace" if "http" in datos else "código"

        bot = Bot(token=TOKEN)
        await bot.send_message(chat_id=user_id, text=f"✅ Tu {tipo_dato} es: {datos}")
        await update.message.reply_text("📤 Datos enviados.")

    except Exception as e:
        print(f"❌ Error en /enviar: {e}")
        await update.message.reply_text("⚠️ Error enviando los datos.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Bienvenido al bot.\n\n"
        "Usa el comando:\n"
        "/buscar correo@ejemplo.com\n"
        "Para iniciar tu solicitud."
    )

async def comando_no_reconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❗ No entendí ese mensaje.\n\n"
        "Usa alguno de estos comandos:\n"
        "/start\n"
        "/buscar\n"
    )

# Comando /add para añadir correos autorizados
async def add_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Uso correcto: /add correo@example.com")
        return

    correo = context.args[0].strip().lower()

    if correo in correos_autorizados:
        await update.message.reply_text("Ese correo ya está autorizado.")
    else:
        correos_autorizados.add(correo)
        guardar_correos_autorizados(correos_autorizados)
        await update.message.reply_text(f"✅ Correo añadido: {correo}")

# --- Función principal con reinicio automático ---
def main():
    threading.Thread(target=run_flask).start()

    while True:
        try:
            app_telegram = ApplicationBuilder().token(TOKEN).build()

            app_telegram.add_handler(CommandHandler("buscar", buscar))
            app_telegram.add_handler(CallbackQueryHandler(opcion_elegida))
            app_telegram.add_handler(CommandHandler("enviar", enviar))
            app_telegram.add_handler(CommandHandler("start", start))
            app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, comando_no_reconocido))
            app_telegram.add_handler(CommandHandler("add", add_email))

            print("🤖 Bot iniciado correctamente...")
            app_telegram.run_polling()

        except Exception as e:
            print(f"❌ Error crítico en run_polling(): {e}")
            print("🔄 Reiniciando bot automáticamente en 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    main()
