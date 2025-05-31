from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
import json
import pandas as pd # Import pandas here for formatting timestamp
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOLS_TO_WATCH, CANDLE_INTERVAL, CANDLE_LIMIT, ORDERBOOK_LIMIT
from analyzer import get_combined_analysis

# Hàm xử lý lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chào mừng! Tôi là bot phân tích crypto. Dùng /analyze <symbol> để phân tích.")

# Hàm xử lý lệnh /analyze
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Vui lòng cung cấp symbol. Ví dụ: /analyze BTCUSDT")
        return

    symbol = args[0].upper()
    # Bạn có thể thêm logic để chọn sàn nếu muốn (ví dụ: /analyze BTCUSDT binance)
    source = args[1].lower() if len(args) > 1 else 'binance'

    await update.message.reply_text(f"Đang phân tích {symbol} từ {source}...")

    analysis_result = get_combined_analysis(symbol, CANDLE_INTERVAL, CANDLE_LIMIT, ORDERBOOK_LIMIT, source)

    if "error" in analysis_result:
        await update.message.reply_text(f"Lỗi: {analysis_result['error']}")
    else:
        # Format kết quả để gửi qua Telegram
        message = f"--- Phân tích cho {analysis_result['symbol']} ({analysis_result['source']}) ---\n\n"

        # Tín hiệu từ Pine Script logic
        price_signals = analysis_result.get('latest_price_signals', {})
        if price_signals:
            message += "**Tín hiệu giá (@MSB OB.pine logic - đơn giản hóa):**\n"
            message += f"- RSI: {price_signals.get('RSI', 'N/A'):.2f} (Overbought: {price_signals.get('RSI_Overbought', False)}, Oversold: {price_signals.get('RSI_Oversold', False)})\n"
            message += f"- Body Spike: Up={price_signals.get('Body_Spike_Up', False)}, Down={price_signals.get('Body_Spike_Down', False)}\n"
            message += f"- Bullish Signal Count: {int(price_signals.get('Bullish_Signal_Count', 0))}\n"
            message += f"- Bearish Signal Count: {int(price_signals.get('Bearish_Signal_Count', 0))}\n"
            # Thêm các tín hiệu khác khi bạn mở rộng analyzer.py
            message += "\n"

        # Phân tích Orderbook (dấu hiệu MM/cá mập)
        orderbook_analysis = analysis_result.get('orderbook_analysis', {})
        if orderbook_analysis:
            message += "**Phân tích Orderbook (dấu hiệu MM/cá mập):**\n"
            message += f"- Tỷ lệ Bid/Ask Volume: {orderbook_analysis.get('imbalance_ratio', 'N/A'):.2f}\n"
            if orderbook_analysis.get('large_bid_wall'):
                wall = orderbook_analysis['large_bid_wall']
                message += f"- Wall mua lớn: Giá {wall['price']}, Khối lượng {wall['amount']:.2f}\n"
            if orderbook_analysis.get('large_ask_wall'):
                wall = orderbook_analysis['large_ask_wall']
                message += f"- Wall bán lớn: Giá {wall['price']}, Khối lượng {wall['amount']:.2f}\n"
            # Thêm các phân tích orderbook khác khi bạn mở rộng analyzer.py
            message += "\n"

        message += f"Thời gian phân tích: {pd.to_datetime(analysis_result['timestamp'], unit='ms')}\n"
        message += "--- Hết phân tích ---"

        await update.message.reply_text(message)

# Hàm chính chạy bot
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Đăng ký các hàm xử lý lệnh
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analyze", analyze_command))

    # Chạy bot
    print("Bot đang chạy...")
    application.run_polling()

if __name__ == '__main__':
    # Ensure config is correctly set before running
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN" or TELEGRAM_CHAT_ID == "YOUR_TELEGRAM_CHAT_ID":
        print("ERROR: Please update config.py with your Telegram Bot Token and Chat ID.")
    else:
        main() 