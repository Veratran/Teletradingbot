# Tradingview Telebot

Bot Telegram phân tích Crypto kết hợp tín hiệu giá (Pine Script logic) và Orderbook.

## Tính năng

- Lấy dữ liệu nến và orderbook từ Binance, Kucoin.
- Phân tích tín hiệu dựa trên logic indicator (đơn giản hóa từ @MSB OB.pine).
- Phân tích orderbook để tìm dấu hiệu Market Maker / Cá Mập (imbalance, wall).
- Gửi kết quả phân tích về Telegram.

## Cài đặt

1.  **Clone hoặc tải project** về máy.
2.  **Cài đặt Python** (nên dùng Python 3.8 trở lên).
3.  **Cài đặt các thư viện** cần thiết:
    ```bash
    cd path/to/Tradingview telebot
    pip install -r requirements.txt
    ```
4.  **Cấu hình bot**: Mở file `config.py` và điền thông tin của bạn:
    -   `TELEGRAM_BOT_TOKEN`: Lấy từ BotFather trên Telegram.
    -   `TELEGRAM_CHAT_ID`: Chat ID của bạn hoặc group muốn nhận tín hiệu (dùng `@userinfobot` để lấy ID).
    -   (Tùy chọn) API keys của Binance, Kucoin nếu cần.

## Cách chạy

1.  Mở terminal/cmd và vào thư mục project.
2.  Chạy file `bot.py`:
    ```bash
    python bot.py
    ```
    Bot sẽ chạy và chờ lệnh từ Telegram.

## Sử dụng Bot

- Gửi `/start` để bắt đầu.
- Gửi `/analyze <SYMBOL> [SOURCE]` để phân tích.
    -   `<SYMBOL>`: Cặp coin muốn phân tích (ví dụ: BTCUSDT).
    -   `[SOURCE]` (tùy chọn): Sàn giao dịch (ví dụ: binance, kucoin). Mặc định là binance.
    -   Ví dụ: `/analyze ETHUSDT kucoin`

## Mở rộng

- Mở rộng logic phân tích trong `analyzer.py` (thêm các indicator khác từ @MSB OB.pine, logic orderbook phức tạp hơn).
- Tích hợp WebSocket để nhận dữ liệu realtime.
- Thêm các lệnh bot khác (`/subscribe`, `/settings`, v.v.).
- Cải thiện định dạng message Telegram.

## Lưu ý
- Bot chỉ gửi tín hiệu khi phát hiện điều kiện đặc biệt (orderbook wall, imbalance, spike, RSI, ATR...)
- Có thể mở rộng thêm sàn, thêm logic phân tích theo ý bạn.
- Không thể truyền trực tiếp orderbook vào Pine Script, chỉ gửi tín hiệu về Telegram. 