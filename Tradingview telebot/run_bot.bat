@echo off
REM Thay đổi thư mục làm việc đến thư mục dự án bot
cd "c:\Users\kanu\Desktop\Tradingview telebot"

REM Kích hoạt virtual environment
REM Đảm bảo bạn đã tạo virtual environment bằng `python -m venv venv` và đã chạy `pip install -r requirements.txt`
REM Nếu tên virtual environment của bạn khác 'venv', hãy thay đổi dòng dưới
call venv\Scripts\activate

REM Chạy script bot Python
REM Sử dụng start để mở bot trong cửa sổ console riêng
start python bot.py

REM Dòng pause này có thể gây treo Task Scheduler nếu bot chạy mãi mãi.
REM Bỏ dấu REM phía trước nếu bạn muốn test script batch bằng cách click đúp và xem kết quả.
REM pause 