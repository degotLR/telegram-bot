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
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6605787552
ARCHIVO_CORREOS = "correos_autorizados.json"
solicitudes_pendientes = {}

# --- Funciones de almacenamiento con JSON ---

def obtener_correos():
    try:
        with open(ARCHIVO_CORREOS, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_correos(data):
    with open(ARCHIVO_CORREOS, 'w') as f:
        json.dump(data, f, indent=4)

def agregar_correo(correo, usuario):
    data = obtener_correos()
    data[correo] = usuario
    guardar_correos(data)
    return True

def eliminar_correo(correo):
    data = obtener_correos()
    if correo in data:
        del data[correo]
        guardar_correos(data)
        return True
    return False

# --- Comandos del bot ---

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        args = context.args

        if not args:
            await update.message.reply_text("❗ Usa el comando así: /buscar correo@ejemplo.com")
            return

        correo = args[0].lower()
        correos = obtener_correos()

        if correo not in correos:
            await update.message.reply_text("❌ Ese correo no está autorizado.")
            return

        usuario_asociado = correos[correo]
        solicitudes_pendientes[user.id] = correo

        botones = [
            [InlineKeyboardButton("🏖️ Estoy de viaje", callback_data='viaje')],
            [InlineKeyboardButton("🏠 Actualizar hogar", callback_data='hogar')],
            [InlineKeyboardButton("🔐 Cambiar contraseña", callback_data='cambiar')],
            [InlineKeyboardButton("📧 Código de inicio", callback_data='codigo')]
        ]
        teclado = InlineKeyboardMarkup(botones)

        await update.message.reply_text(
            f"🔎 Correo validado ✅\nUsuario autorizado: {usuario_asociado}\n\nElige una opción:",
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

        await query.edit_message_text("🔍 Procesando... Por favor espera (30-60 seg)...")

        bot = Bot(token=TOKEN)
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 Solicitud recibida:\n👤 Usuario: @{query.from_user.username} (ID: {user_id})\n📧 Correo: {correo}\n🛠️ Opción elegida: {texto_opcion}"
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
        "👋 ¡Hola! Bienvenido al bot.\n\nUsa el comando:\n/buscar correo@ejemplo.com\nPara iniciar tu solicitud."
    )

async def comando_no_reconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❗ No entendí eso. Usa /start o /buscar.")

# /add correo@ejemplo.com usuario
async def add_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❗ Uso correcto: /add correo@example.com usuario")
        return

    correo = context.args[0].strip().lower()
    usuario = context.args[1].strip()

    correos = obtener_correos()
    if correo in correos:
        await update.message.reply_text("Ese correo ya está autorizado.")
        return

    agregar_correo(correo, usuario)
    await update.message.reply_text(f"✅ Correo añadido: {correo} con usuario: {usuario}")

# /delete correo@ejemplo.com
async def delete_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    if not context.args:
        await update.message.reply_text("❗ Uso correcto: /delete correo@example.com")
        return

    correo = context.args[0].strip().lower()
    if eliminar_correo(correo):
        await update.message.reply_text(f"✅ Correo eliminado: {correo}")
    else:
        await update.message.reply_text("❌ Ese correo no está autorizado.")

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
            app_telegram.add_handler(CommandHandler("add", add_email))
            app_telegram.add_handler(CommandHandler("delete", delete_email))
            app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, comando_no_reconocido))

            print("🤖 Bot iniciado correctamente...")
            app_telegram.run_polling()

        except Exception as e:
            print(f"❌ Error crítico en run_polling(): {e}")
            print("🔄 Reiniciando bot automáticamente en 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    main()
