"""
SmartTrade Insights - Desktop Notification Alerts
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_plyer_available: Optional[bool] = None


def _check_plyer() -> bool:
    global _plyer_available
    if _plyer_available is None:
        try:
            from plyer import notification  # noqa: F401
            _plyer_available = True
        except ImportError:
            _plyer_available = False
            logger.debug("plyer not available – desktop alerts disabled")
    return _plyer_available


def send_alert(
    title: str,
    message: str,
    ticker: str = "",
    signal: str = "",
    timeout: int = 8,
):
    """Send a desktop notification if plyer is available."""
    if not _check_plyer():
        logger.info("ALERT [%s] %s – %s", ticker, title, message)
        return

    try:
        from plyer import notification
        notification.notify(
            title=f"SmartTrade – {title}",
            message=message,
            app_name="SmartTrade Insights",
            timeout=timeout,
        )
    except Exception as e:
        logger.warning("Desktop alert failed: %s", e)


def send_signal_alert(ticker: str, signal: str, price: float, strength: float):
    """Convenience wrapper for buy/sell signal alerts."""
    emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
    title = f"{emoji} {signal} signal – {ticker}"
    message = (
        f"{ticker} @ ${price:.2f}\n"
        f"Signal strength: {strength:.0f}%"
    )
    send_alert(title=title, message=message, ticker=ticker, signal=signal)


def send_price_alert(ticker: str, price: float, threshold: float, direction: str):
    """Price-level alert."""
    direction_str = "above" if direction == "up" else "below"
    title = f"Price Alert – {ticker}"
    message = f"{ticker} is now {direction_str} ${threshold:.2f}\nCurrent: ${price:.2f}"
    send_alert(title=title, message=message, ticker=ticker)
