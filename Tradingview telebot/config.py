
# Telegram Bot API Token - Lấy từ BotFather trên Telegram
TELEGRAM_BOT_TOKEN = "7344243113:AAFCaUCJuzfk9PDa1Yz5zQpZoGPazgka5i8"

# Chat ID của bạn hoặc group muốn nhận tín hiệu - Lấy bằng cách gửi tin nhắn cho bot @userinfobot
TELEGRAM_CHAT_ID = "6359400859"

# Binance API Key và Secret (Tùy chọn, nếu cần request riêng tư hoặc rate limit cao hơn)
BINANCE_API_KEY = "YOUR_BINANCE_API_KEY"
BINANCE_API_SECRET = "YOUR_BINANCE_API_SECRET"

# KuCoin API Key, Secret, và Passphrase (Tùy chọn)
KUCOIN_API_KEY = "683af2dd55fba5000107ac55"
KUCOIN_API_SECRET = "56bb6513-681e-46cb-83c6-da43518add14"
KUCOIN_PASSPHRASE = "741268"

# Các cặp coin muốn theo dõi (ví dụ)
SYMBOLS_TO_WATCH = ["BTCUSDT", "AI16ZUSDT"]

# Khoảng thời gian (interval) cho dữ liệu nến (Pine Script logic)
CANDLE_INTERVAL = "1m" # Hoặc "5m", "15m", "1h", v.v.

# Số lượng nến lịch sử cần lấy để tính indicator
CANDLE_LIMIT = 500

# Số lượng level orderbook cần lấy (ví dụ 20 bids/asks)
ORDERBOOK_LIMIT = 20

# Threshold cho phân tích orderbook (ví dụ: imbalance > 2x, wall > 100 BTC,...)
# Bạn cần điều chỉnh các ngưỡng này dựa trên chiến lược của mình
ORDERBOOK_IMBALANCE_THRESHOLD = 2 # bids/asks ratio
ORDERBOOK_WALL_THRESHOLD_BTC = 100 # khối lượng wall tối thiểu (đổi sang USDT tùy coin)

# Ví dụ lấy chat_id: nhắn /start cho bot, sau đó xem log hoặc dùng @userinfobot 