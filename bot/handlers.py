import logging
from typing import Optional

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import messages
from models.database import Alert, SessionLocal, User
from services.alerts import check_all_alerts
from services.mercadolibre import (
    extract_item_id,
    format_price,
    get_item,
    parse_price,
    search_products,
)

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_or_create_user(db, telegram_user) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_user.id).first()
    if not user:
        user = User(telegram_id=telegram_user.id, username=telegram_user.username or "")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def _do_search(
    query: str, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        messages.SEARCHING.format(query=query), parse_mode=ParseMode.HTML
    )
    try:
        results = await search_products(query, limit=5)
    except Exception:
        logger.exception("Error searching ML for %r", query)
        await update.message.reply_text(
            messages.SEARCH_ERROR, parse_mode=ParseMode.HTML
        )
        return

    if not results:
        await update.message.reply_text(
            messages.SEARCH_NO_RESULTS.format(query=query), parse_mode=ParseMode.HTML
        )
        return

    # Store results so callbacks can reference them by index
    context.user_data["search_results"] = results

    text = messages.SEARCH_HEADER.format(query=query)
    keyboard = []
    for i, item in enumerate(results):
        text += messages.SEARCH_ITEM_INLINE.format(
            num=i + 1,
            title=item.get("title", "Sin título")[:60],
            price=format_price(item.get("price", 0)),
            url=item.get("permalink", ""),
        )
        label = (
            f"📌 {item.get('title', '')[:30]}… • {format_price(item.get('price', 0))}"
        )
        keyboard.append([InlineKeyboardButton(label, callback_data=f"seguir:{i}")])

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Command handlers ──────────────────────────────────────────────────────────


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = update.effective_user.first_name or "amigo"
    await update.message.reply_text(
        messages.WELCOME.format(name=name), parse_mode=ParseMode.HTML
    )


async def ayuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(messages.HELP, parse_mode=ParseMode.HTML)


async def buscar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            messages.SEARCH_NO_ARGS, parse_mode=ParseMode.HTML
        )
        return
    await _do_search(" ".join(context.args), update, context)


async def seguir_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            messages.SEGUIR_NO_ARGS, parse_mode=ParseMode.HTML
        )
        return

    item_id = extract_item_id(context.args[0])
    if not item_id:
        await update.message.reply_text(
            messages.SEGUIR_INVALID_ID, parse_mode=ParseMode.HTML
        )
        return

    target_price = parse_price(context.args[1])
    if target_price is None:
        await update.message.reply_text(
            messages.SEGUIR_INVALID_PRICE, parse_mode=ParseMode.HTML
        )
        return

    await _create_alert(item_id, target_price, update, context)


async def mis_alertas_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    db = SessionLocal()
    try:
        user = _get_or_create_user(db, update.effective_user)
        alerts = (
            db.query(Alert)
            .filter(Alert.user_id == user.id, Alert.is_active == True)  # noqa: E712
            .order_by(Alert.created_at.desc())
            .all()
        )

        if not alerts:
            await update.message.reply_text(
                messages.ALERTS_EMPTY, parse_mode=ParseMode.HTML
            )
            return

        text = messages.ALERTS_HEADER.format(count=len(alerts))
        keyboard = []
        for i, alert in enumerate(alerts, 1):
            text += messages.ALERT_ITEM.format(
                num=i,
                name=alert.item_name,
                target_price=format_price(alert.target_price),
                current_price=format_price(alert.current_price or 0),
                url=alert.item_url,
            )
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🗑 Eliminar #{i}: {alert.item_name[:25]}…",
                        callback_data=f"borrar:{alert.id}",
                    )
                ]
            )

        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    finally:
        db.close()


async def borrar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            messages.BORRAR_NO_ARGS, parse_mode=ParseMode.HTML
        )
        return
    try:
        alert_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            messages.BORRAR_INVALID_ID, parse_mode=ParseMode.HTML
        )
        return
    await _delete_alert(alert_id, update, context)


# ── Text message handler (free-text search + price reply) ────────────────────


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    # If we're waiting for a price after the user tapped "📌 Seguir"
    pending = context.user_data.get("pending_follow")
    if pending:
        target_price = parse_price(text)
        if target_price is None:
            await update.message.reply_text(
                messages.ASK_PRICE_INVALID, parse_mode=ParseMode.HTML
            )
            return
        context.user_data.pop("pending_follow")
        await _create_alert(
            pending["item_id"], target_price, update, context, item_hint=pending
        )
        return

    # Otherwise treat message as a search query
    await _do_search(text, update, context)


# ── Callback query handlers ───────────────────────────────────────────────────


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("seguir:"):
        idx = int(data.split(":")[1])
        results = context.user_data.get("search_results", [])
        if idx >= len(results):
            await query.message.reply_text(
                "⚠️ Resultado no disponible, realiza una nueva búsqueda."
            )
            return
        item = results[idx]
        context.user_data["pending_follow"] = {
            "item_id": item["id"],
            "title": item.get("title", "Producto"),
            "price": item.get("price", 0),
            "url": item.get("permalink", ""),
        }
        await query.message.reply_text(
            messages.ASK_PRICE.format(
                title=item.get("title", "")[:60],
                current_price=format_price(item.get("price", 0)),
            ),
            parse_mode=ParseMode.HTML,
        )

    elif data.startswith("borrar:"):
        alert_id = int(data.split(":")[1])
        await _delete_alert(alert_id, update, context, via_callback=True)


# ── Shared logic ──────────────────────────────────────────────────────────────


async def _create_alert(
    item_id: str,
    target_price: float,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    item_hint: Optional[dict] = None,
) -> None:
    msg = update.message or update.callback_query.message

    await msg.reply_text(messages.VERIFYING, parse_mode=ParseMode.HTML)
    try:
        item = await get_item(item_id)
    except Exception:
        logger.exception("Error fetching item %s", item_id)
        await msg.reply_text(messages.SEGUIR_ERROR, parse_mode=ParseMode.HTML)
        return

    if item is None:
        # If we have a hint from search results, use that data instead of failing
        if item_hint:
            item = {
                "id": item_hint["item_id"],
                "title": item_hint["title"],
                "price": item_hint["price"],
                "permalink": item_hint["url"],
            }
        else:
            await msg.reply_text(
                messages.SEGUIR_ITEM_NOT_FOUND, parse_mode=ParseMode.HTML
            )
            return

    current_price: float = item.get("price", 0)
    item_name: str = item.get("title", "Producto")
    item_url: str = item.get("permalink", "https://www.mercadolibre.cl")

    db = SessionLocal()
    try:
        user = _get_or_create_user(db, update.effective_user)
        existing = (
            db.query(Alert)
            .filter(
                Alert.user_id == user.id,
                Alert.item_id == item_id,
                Alert.is_active == True,
            )  # noqa: E712
            .first()
        )
        if existing:
            await msg.reply_text(
                messages.SEGUIR_ALREADY_EXISTS.format(
                    name=existing.item_name,
                    target_price=format_price(existing.target_price),
                    current_price=format_price(existing.current_price or current_price),
                ),
                parse_mode=ParseMode.HTML,
            )
            return

        alert = Alert(
            user_id=user.id,
            item_id=item_id,
            item_name=item_name,
            item_url=item_url,
            target_price=target_price,
            current_price=current_price,
            is_active=True,
        )
        db.add(alert)
        db.commit()

        if current_price <= target_price:
            await msg.reply_text(
                messages.SEGUIR_CREATED_BELOW.format(
                    name=item_name,
                    current_price=format_price(current_price),
                    target_price=format_price(target_price),
                    url=item_url,
                ),
                parse_mode=ParseMode.HTML,
            )
        else:
            await msg.reply_text(
                messages.SEGUIR_CREATED.format(
                    name=item_name,
                    current_price=format_price(current_price),
                    target_price=format_price(target_price),
                ),
                parse_mode=ParseMode.HTML,
            )
    finally:
        db.close()


async def _delete_alert(
    alert_id: int,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    via_callback: bool = False,
) -> None:
    msg = update.callback_query.message if via_callback else update.message
    db = SessionLocal()
    try:
        user = _get_or_create_user(db, update.effective_user)
        alert = (
            db.query(Alert)
            .filter(Alert.id == alert_id, Alert.user_id == user.id)
            .first()
        )
        if not alert:
            await msg.reply_text(
                messages.BORRAR_NOT_FOUND.format(id=alert_id), parse_mode=ParseMode.HTML
            )
            return
        name = alert.item_name
        db.delete(alert)
        db.commit()
        await msg.reply_text(
            messages.BORRAR_SUCCESS_NAME.format(name=name), parse_mode=ParseMode.HTML
        )
    finally:
        db.close()


async def _check_prices_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await check_all_alerts(context.bot)


# ── Application factory ───────────────────────────────────────────────────────


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("buscar", "Buscar un producto en MercadoLibre"),
            BotCommand("mis_alertas", "Ver tus alertas activas"),
            BotCommand("ayuda", "Ver todos los comandos"),
        ]
    )


def build_application(token: str) -> Application:
    application = Application.builder().token(token).post_init(_post_init).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("buscar", buscar_command))
    application.add_handler(CommandHandler("seguir", seguir_command))
    application.add_handler(CommandHandler("mis_alertas", mis_alertas_command))
    application.add_handler(CommandHandler("borrar", borrar_command))
    application.add_handler(CommandHandler("ayuda", ayuda_command))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    application.job_queue.run_repeating(_check_prices_job, interval=1800, first=60)

    return application
