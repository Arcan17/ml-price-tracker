from unittest.mock import AsyncMock, patch

from services.alerts import check_all_alerts

ITEM_ABOVE_TARGET = {
    "id": "MLC123456789",
    "title": "iPhone 15 128GB Negro",
    "price": 900_000,
    "permalink": "https://articulo.mercadolibre.cl/MLC-123456789-iphone-15",
}

ITEM_BELOW_TARGET = {
    "id": "MLC123456789",
    "title": "iPhone 15 128GB Negro",
    "price": 800_000,
    "permalink": "https://articulo.mercadolibre.cl/MLC-123456789-iphone-15",
}


# ── Price drops → alert fires ─────────────────────────────────────────────────


async def test_alert_triggered_when_price_drops(
    db_session, db_session_factory, sample_alert
):
    with patch(
        "services.alerts.get_item", new=AsyncMock(return_value=ITEM_BELOW_TARGET)
    ):
        mock_bot = AsyncMock()
        await check_all_alerts(mock_bot, session_factory=db_session_factory)

    mock_bot.send_message.assert_called_once()
    kwargs = mock_bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == sample_alert.user.telegram_id
    assert "Bajó" in kwargs["text"]

    db_session.refresh(sample_alert)
    assert sample_alert.is_active is False
    assert sample_alert.triggered_at is not None
    assert sample_alert.current_price == 800_000


# ── Price still above → no notification ──────────────────────────────────────


async def test_alert_not_triggered_when_price_above(
    db_session, db_session_factory, sample_alert
):
    with patch(
        "services.alerts.get_item", new=AsyncMock(return_value=ITEM_ABOVE_TARGET)
    ):
        mock_bot = AsyncMock()
        await check_all_alerts(mock_bot, session_factory=db_session_factory)

    mock_bot.send_message.assert_not_called()

    db_session.refresh(sample_alert)
    assert sample_alert.is_active is True
    assert sample_alert.current_price == 900_000


# ── Product removed from ML ───────────────────────────────────────────────────


async def test_alert_deactivated_when_product_removed(
    db_session, db_session_factory, sample_alert
):
    with patch("services.alerts.get_item", new=AsyncMock(return_value=None)):
        mock_bot = AsyncMock()
        await check_all_alerts(mock_bot, session_factory=db_session_factory)

    mock_bot.send_message.assert_called_once()
    assert "no está disponible" in mock_bot.send_message.call_args.kwargs["text"]

    db_session.refresh(sample_alert)
    assert sample_alert.is_active is False


# ── No alerts → nothing happens ───────────────────────────────────────────────


async def test_no_alerts_does_nothing(db_session_factory):
    mock_bot = AsyncMock()
    await check_all_alerts(mock_bot, session_factory=db_session_factory)
    mock_bot.send_message.assert_not_called()


# ── Inactive alerts are skipped ───────────────────────────────────────────────


async def test_inactive_alerts_are_skipped(
    db_session, db_session_factory, sample_alert
):
    sample_alert.is_active = False
    db_session.commit()

    mock_bot = AsyncMock()
    await check_all_alerts(mock_bot, session_factory=db_session_factory)
    mock_bot.send_message.assert_not_called()


# ── At-target price also triggers ────────────────────────────────────────────


async def test_alert_triggers_at_exact_target_price(
    db_session, db_session_factory, sample_alert
):
    item_at_target = {**ITEM_ABOVE_TARGET, "price": sample_alert.target_price}

    with patch("services.alerts.get_item", new=AsyncMock(return_value=item_at_target)):
        mock_bot = AsyncMock()
        await check_all_alerts(mock_bot, session_factory=db_session_factory)

    mock_bot.send_message.assert_called_once()

    db_session.refresh(sample_alert)
    assert sample_alert.is_active is False
