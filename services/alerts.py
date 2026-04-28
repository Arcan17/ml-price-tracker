import logging
from datetime import datetime

from sqlalchemy.orm import Session, joinedload
from telegram import Bot
from telegram.constants import ParseMode

from bot import messages
from models.database import Alert, SessionLocal
from services.mercadolibre import format_price, get_item

logger = logging.getLogger(__name__)


async def check_all_alerts(bot: Bot, session_factory=None) -> None:
    """Check all active alerts and notify users when a price target is hit."""
    factory = session_factory or SessionLocal
    db: Session = factory()
    try:
        alerts = (
            db.query(Alert)
            .filter(Alert.is_active == True)  # noqa: E712
            .options(joinedload(Alert.user))
            .all()
        )
        logger.info("Checking %d active alert(s)", len(alerts))

        for alert in alerts:
            try:
                await _check_single_alert(alert, db, bot)
            except Exception:
                logger.exception("Error checking alert %d", alert.id)

        db.commit()
    except Exception:
        logger.exception("Unexpected error in check_all_alerts")
        db.rollback()
    finally:
        db.close()


async def _check_single_alert(alert: Alert, db: Session, bot: Bot) -> None:
    item = await get_item(alert.item_id)

    if item is None:
        logger.info("Alert %d: product %s no longer available", alert.id, alert.item_id)
        alert.is_active = False
        await bot.send_message(
            chat_id=alert.user.telegram_id,
            text=messages.ALERT_PRODUCT_REMOVED.format(name=alert.item_name),
            parse_mode=ParseMode.HTML,
        )
        return

    current_price: float = item.get("price", 0)
    alert.current_price = current_price

    if current_price <= alert.target_price:
        logger.info(
            "Alert %d triggered: %.0f <= %.0f",
            alert.id, current_price, alert.target_price,
        )
        alert.is_active = False
        alert.triggered_at = datetime.utcnow()
        await bot.send_message(
            chat_id=alert.user.telegram_id,
            text=messages.ALERT_TRIGGERED.format(
                name=alert.item_name,
                current_price=format_price(current_price),
                target_price=format_price(alert.target_price),
                url=alert.item_url,
            ),
            parse_mode=ParseMode.HTML,
        )
