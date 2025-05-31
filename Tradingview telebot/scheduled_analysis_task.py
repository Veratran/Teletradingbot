import asyncio
import pandas as pd
from telegram import Bot
from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    SYMBOLS_TO_WATCH,
    CANDLE_INTERVAL,
    CANDLE_LIMIT,
    ORDERBOOK_LIMIT
)
from analyzer import get_combined_analysis
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def run_scheduled_analysis():
    """Runs analysis for configured symbols and sends results to Telegram."""
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID":
        logging.error("Telegram BOT_TOKEN or CHAT_ID not set in config.py")
        return

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    logging.info("Starting scheduled analysis for symbols...")

    for symbol_info in SYMBOLS_TO_WATCH:
        symbol = symbol_info["symbol"].upper()
        source = symbol_info.get("source", "binance").lower() # Default to binance

        logging.info(f"Analyzing {symbol} from {source}...")

        try:
            # Sử dụng hàm get_combined_analysis đã có
            analysis_result = get_combined_analysis(
                symbol,
                CANDLE_INTERVAL, # Có thể cấu hình interval/limit riêng cho scheduled task nếu cần
                CANDLE_LIMIT,
                ORDERBOOK_LIMIT,
                source
            )

            if "error" in analysis_result:
                message = f"⚠️ Lỗi phân tích {symbol} từ {source}: {analysis_result['error']}"
                logging.error(message)
            else:
                # Format kết quả tương tự như trong bot.py analyze_command
                message = f"--- Phân tích định kỳ cho {analysis_result['symbol']} ({analysis_result['source']}) ---\\n\\n"

                # Tín hiệu giá (đơn giản hóa)
                price_signals = analysis_result.get('latest_price_signals', {})
                if price_signals:
                    message += "**Tín hiệu giá:**\\n"
                    message += f"- RSI: {price_signals.get('RSI', 'N/A'):.2f} (Overbought: {price_signals.get('RSI_Overbought', False)}, Oversold: {price_signals.get('RSI_Oversold', False)})\\n"
                    message += f"- Body Spike: Up={price_signals.get('Body_Spike_Up', False)}, Down={price_signals.get('Body_Spike_Down', False)}\\n"
                    # Thêm các tín hiệu khác khi bạn mở rộng analyzer.py
                    message += "\\n"

                # Phân tích Orderbook
                orderbook_analysis = analysis_result.get('orderbook_analysis', {})
                if orderbook_analysis:
                    message += "**Phân tích Orderbook:**\\n"
                    message += f"- Tỷ lệ Bid/Ask Volume: {orderbook_analysis.get('imbalance_ratio', 'N/A'):.2f}\\n"
                    if orderbook_analysis.get('large_bid_wall'):
                        wall = orderbook_analysis['large_bid_wall']
                        message += f"- Wall mua lớn: Giá {wall['price']}, Khối lượng {wall['amount']:.2f}\\n"
                    if orderbook_analysis.get('large_ask_wall'):
                        wall = orderbook_analysis['large_ask_wall']
                        message += f"- Wall bán lớn: Giá {wall['price']}, Khối lượng {wall['amount']:.2f}\\n"
                    message += "\\n"

                 # Mẫu hình nến
                candlestick_patterns = analysis_result.get('candlestick_patterns', [])
                if candlestick_patterns:
                    message += "**Mẫu hình nến:**\\n"
                    message += f"- Các mẫu hình được nhận diện: {', '.join(candlestick_patterns) or 'Không có'}\\n"
                    message += "\\n"

                message += f"Thời gian phân tích: {pd.to_datetime(analysis_result['timestamp'], unit='ms')}\\n"
                message += "--- Hết phân tích ---\\n"


            # Gửi tin nhắn
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            logging.info(f"Analysis result sent for {symbol}.")

        except Exception as e:
            error_message = f"⚠️ Lỗi khi chạy phân tích định kỳ cho {symbol} từ {source}: {e}"
            logging.error(error_message, exc_info=True)
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=error_message)


if __name__ == "__main__":
    # SYMBOLS_TO_WATCH = [{"symbol": "BTCUSDT", "source": "binance"}, {"symbol": "ETHUSDT"}] # Define in config.py
    asyncio.run(run_scheduled_analysis()) 