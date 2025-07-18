from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# Tu TOKEN del bot
TOKEN = '7643585666:AAFpCxF2rbnPx5hhfcAPFQ_TGYu2hpUZhjk'
ADMIN_ID = 6605787552 # Tu ID personal de Telegram

solicitudes_pendientes = {}  # user_id: correo

# Lista de correos permitidos
CORREOS_AUTORIZADOS = [
    "sestgo19@gmail.com",
    "sestgo22@gmail.com",
    "sestgo6@gmail.com" ,
    "sestgo11@gmail.com"
]

# /buscar comando con verificación
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text("❗ Usa el comando así: /buscar correo@ejemplo.com")
        return

    correo = args[0].lower()

    if correo not in CORREOS_AUTORIZADOS:
        await update.message.reply_text("❌ Ese correo no está autorizado para hacer solicitudes.")
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

# Respuesta a la opción elegida
async def opcion_elegida(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    # Mensaje visible para el usuario
    await query.edit_message_text("🔍 Buscando datos... Por favor espera... Tiempo estimado (30-60 seg)...")

    # Notificación al admin
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

# Función para que el admin envíe códigos usando /enviar
async def enviar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❗ Usa el comando así: /enviar ID_USUARIO código_a_enviar")
        return

    user_id = int(args[0])
    codigo = ' '.join(args[1:])

    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=user_id, text=f"✅ La respuesta a tu solicitud es: {codigo}")
    await update.message.reply_text("📤 Datos enviados.")  

# Función para el comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Bienvenido al bot de SestGo.\n\n"
        "Usa el comando:\n"
        "/buscar correo@ejemplo.com\n"
        "Para tu solicitud.\n\n"
        "🔐 Tu solicitud será atendida lo antes posible."
    )

# Función para mensajes no reconocidos
async def comando_no_reconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❗ No entendí ese mensaje.\n\n"
        "Usa alguno de estos comandos:\n"
        "/start\n"
        "/buscar\n"
        "/ayuda\n"
    )# Función para mensajes no reconocidoss

# Ejecutar el bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("buscar", buscar))
app.add_handler(CallbackQueryHandler(opcion_elegida))
app.add_handler(CommandHandler("enviar", enviar))
app.add_handler(CommandHandler("start", start))
# Captura cualquier texto que NO sea comando
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, comando_no_reconocido))


print("🤖 Bot iniciado...")
app.run_polling()
