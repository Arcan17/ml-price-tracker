WELCOME = (
    "👋 <b>¡Hola {name}!</b> Soy tu asistente de precios de MercadoLibre Chile.\n\n"
    "Te aviso cuando el precio de tus productos favoritos baje al valor que quieres pagar 🎯\n\n"
    "<b>¿Cómo funciono?</b>\n"
    "1. Escribe el nombre de cualquier producto y te muestro resultados\n"
    "2. Toca <b>📌 Seguir</b> en el que te interese\n"
    "3. Dime el precio objetivo y listo ✅\n\n"
    "Escribe /ayuda para ver todos los comandos."
)

HELP = (
    "📖 <b>Comandos disponibles:</b>\n\n"
    "🔍 Escribe cualquier texto para buscar un producto\n"
    "   <i>Ejemplo: iphone 15 pro</i>\n\n"
    "📌 <code>/buscar {nombre}</code>\n"
    "   Busca un producto en MercadoLibre\n\n"
    "📋 <code>/mis_alertas</code>\n"
    "   Ver todas tus alertas activas\n\n"
    "🗑 <code>/borrar {id}</code>\n"
    "   Elimina una alerta por ID\n\n"
    "❓ <code>/ayuda</code>\n"
    "   Muestra este mensaje"
)

SEARCH_HEADER = '🔍 <b>Resultados para "{query}":</b>\n\n'

SEARCH_ITEM_INLINE = (
    "{num}. <b>{title}</b>\n"
    "   💰 {price}\n"
    '   🔗 <a href="{url}">Ver en MercadoLibre</a>\n\n'
)

# Legacy format kept for /seguir command compatibility
SEARCH_ITEM = (
    "{num}. <b>{title}</b>\n"
    "   💰 {price}\n"
    "   🆔 <code>{item_id}</code>\n"
    '   🔗 <a href="{url}">Ver en MercadoLibre</a>\n\n'
)

SEARCH_FOOTER = (
    "💡 Para crear una alerta:\n<code>/seguir {item_id} {precio_objetivo}</code>"
)

SEARCH_NO_RESULTS = (
    '😕 No encontré productos para <b>"{query}"</b>. Intenta con otros términos.'
)

SEARCH_NO_ARGS = (
    "❌ Debes indicar qué buscar.\n<i>Ejemplo: /buscar samsung galaxy s24</i>"
)

SEARCH_ERROR = "⚠️ Hubo un error al buscar. Intenta nuevamente en unos minutos."

ASK_PRICE = (
    "📌 <b>{title}</b>\n"
    "💰 Precio actual: <b>{current_price}</b>\n\n"
    "¿A qué precio quieres que te avise?\n"
    "<i>Escribe solo el número, por ejemplo: 850000</i>"
)

ASK_PRICE_INVALID = (
    "❌ Eso no parece un precio válido.\n\n"
    "Escribe solo el número sin puntos ni símbolos.\n"
    "<i>Ejemplo: 850000</i>"
)

SEGUIR_NO_ARGS = (
    "❌ Formato incorrecto.\n\n"
    "Uso: <code>/seguir {item_id o url} {precio_objetivo}</code>\n"
    "Ejemplo: <code>/seguir MLC1234567890 850000</code>"
)

SEGUIR_INVALID_ID = (
    "❌ No pude identificar el producto.\n\n"
    "Usa el ID del producto (ej: <code>MLC1234567890</code>) o la URL completa de MercadoLibre."
)

SEGUIR_INVALID_PRICE = (
    "❌ El precio no es válido.\n\n"
    "Ingresa solo el número sin puntos ni símbolos.\n"
    "Ejemplo: <code>/seguir MLC1234567890 850000</code>"
)

SEGUIR_ITEM_NOT_FOUND = (
    "❌ No encontré ese producto en MercadoLibre. " "Puede que ya no esté disponible."
)

SEGUIR_ALREADY_EXISTS = (
    "ℹ️ Ya tienes una alerta activa para <b>{name}</b>.\n\n"
    "🎯 Precio objetivo: {target_price}\n"
    "💰 Precio actual: {current_price}\n\n"
    "Usa /mis_alertas para ver todas tus alertas."
)

SEGUIR_CREATED = (
    "✅ <b>¡Alerta creada!</b>\n\n"
    "📦 {name}\n"
    "💰 Precio actual: {current_price}\n"
    "🎯 Te aviso cuando baje de: {target_price}\n\n"
    "Reviso los precios cada 30 minutos 🔄"
)

SEGUIR_CREATED_BELOW = (
    "✅ <b>¡Buenas noticias!</b>\n\n"
    "📦 {name}\n"
    "💰 Precio actual: {current_price}\n"
    "🎯 Tu precio objetivo era: {target_price}\n\n"
    "<b>¡El precio ya está por debajo de tu objetivo!</b> 🎉\n"
    '🛒 <a href="{url}">Ver en MercadoLibre</a>'
)

SEGUIR_ERROR = "⚠️ Hubo un error al crear la alerta. Intenta nuevamente."

ALERTS_HEADER = "📋 <b>Tus alertas activas ({count}):</b>\n\n"

ALERT_ITEM = (
    "{num}. <b>{name}</b>\n"
    "   🎯 Objetivo: {target_price}\n"
    "   💰 Precio actual: {current_price}\n"
    '   🔗 <a href="{url}">Ver producto</a>\n\n'
)

ALERTS_EMPTY = (
    "📭 No tienes alertas activas.\n\n"
    "Escribe el nombre de un producto para buscarlo y crear tu primera alerta."
)

BORRAR_NO_ARGS = "❌ Indica el ID de la alerta.\n<i>Ejemplo: /borrar 3</i>"

BORRAR_INVALID_ID = (
    "❌ El ID debe ser un número. Usa /mis_alertas para ver tus alertas."
)

BORRAR_NOT_FOUND = (
    "❌ No encontré la alerta #{id}. Usa /mis_alertas para ver tus alertas."
)

BORRAR_SUCCESS = "✅ Alerta #{id} eliminada correctamente."

BORRAR_SUCCESS_NAME = "✅ Alerta de <b>{name}</b> eliminada."

ALERT_TRIGGERED = (
    "🔔 <b>¡Bajó el precio!</b>\n\n"
    "📦 {name}\n"
    "💰 Precio actual: {current_price}\n"
    "✅ Tu objetivo era: {target_price}\n\n"
    '🛒 <a href="{url}">Ver en MercadoLibre</a>'
)

ALERT_PRODUCT_REMOVED = (
    "⚠️ <b>Producto no disponible</b>\n\n"
    "El producto <b>{name}</b> ya no está disponible en MercadoLibre.\n"
    "Tu alerta fue eliminada automáticamente."
)

VERIFYING = "⏳ Verificando producto..."
SEARCHING = "🔍 Buscando <b>{query}</b>..."
