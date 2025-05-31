import pandas as pd
import numpy as np
from binance.client import Client
# from kucoin.client import Client as KucoinClient # Tạm bỏ Kucoin WebSocket để đơn giản
import time
import logging # Thêm logging
from config import *

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Kết nối sàn (cho REST requests ban đầu)
binance_client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
# kucoin_client = KucoinClient(api_key=KUCOIN_API_KEY, api_secret=KUCOIN_API_SECRET, passphrase=KUCOIN_PASSPHRASE) # Tạm bỏ Kucoin

def fetch_candles(symbol, interval, limit, source='binance'):
    """Lấy dữ liệu nến từ sàn."""
    try:
        if source == 'binance':
            klines = binance_client.get_historical_klines(symbol, interval, limit=limit)
            candles = [{
                'time': int(k[0]),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            } for k in klines]
        elif source == 'kucoin':
            # Kucoin API interval format có thể khác, cần mapping
            kucoin_interval = {
                "1m": "1min", "5m": "5min", "15m": "15min",
                "1h": "1hour", "4h": "4hour", "1d": "1day", "1w": "1week"
            }.get(interval, interval)
            klines = kucoin_client.get_kline(symbol, kucoin_interval)
            candles = [{
                 'time': int(k[0]) * 1000, # Convert to milliseconds
                 'open': float(k[1]),
                 'close': float(k[2]),
                 'high': float(k[3]),
                 'low': float(k[4]),
                 'volume': float(k[5])
            } for k in klines]

        df = pd.DataFrame(candles)
        if not df.empty:
             df['time'] = pd.to_datetime(df['time'], unit='ms')
             df.set_index('time', inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching candles from {source} for {symbol}: {e}")
        return pd.DataFrame()

def fetch_orderbook(symbol, limit, source='binance'):
    """Lấy dữ liệu orderbook từ sàn."""
    try:
        if source == 'binance':
            depth = binance_client.get_order_book(symbol=symbol, limit=limit)
        elif source == 'kucoin':
            depth = kucoin_client.get_order_book(symbol, limit=limit)
        return depth
    except Exception as e:
        print(f"Error fetching orderbook from {source} for {symbol}: {e}")
        return None

# --- Replicate Pine Script Logic (Helper Functions) ---
# Các hàm tính indicator cơ bản, sẽ dùng trong lớp SymbolAnalyzer

def calculate_ma(data, period):
    return data['close'].rolling(window=period).mean()

def calculate_ema(data, period):
    return data['close'].ewm(span=period, adjust=False).mean()

def calculate_rsi(data, period):
    delta = data['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Sử dụng .ewm cho tính toán trung bình động (giống Pine)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs.fillna(0))) # Fill NaN/inf cho 100 khi avg_loss = 0
    return rsi

# Placeholder for other indicator calculations (MACD, BB, etc.)
# def calculate_macd(data, fast, slow, signal): ...
# def calculate_bb(data, period, mult): ...

def calculate_body(data):
    """Tính toán thân nến (giá đóng cửa - giá mở cửa)."""
    return abs(data['close'] - data['open'])

def calculate_sma(data, period, column='close'):
    """Tính Simple Moving Average."""
    return data[column].rolling(window=period).mean()

def calculate_atr(data, period):
    """Tính Average True Range (ATR)."""
    # Công thức True Range: max[(high - low), abs(high - close[1]), abs(low - close[1])]
    tr1 = data['high'] - data['low']
    tr2 = abs(data['high'] - data['close'].shift(1))
    tr3 = abs(data['low'] - data['close'].shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=period, adjust=False).mean() # Thường dùng EMA cho ATR
    return atr

def analyze_orderbook_snapshot(orderbook):
    """Phân tích orderbook snapshot để tìm dấu hiệu MM/cá mập (dùng trong lớp)."""
    if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
        return None

    bids = pd.DataFrame(orderbook['bids'], columns=['price', 'amount'], dtype=float)
    asks = pd.DataFrame(orderbook['asks'], columns=['price', 'amount'], dtype=float)

    if bids.empty or asks.empty:
        return None

    # Example: Orderbook Imbalance (weighted by price)
    total_bid_value = (bids['amount'] * bids['price']).sum()
    total_ask_value = (asks['amount'] * asks['price']).sum()
    imbalance_ratio = total_bid_value / total_ask_value if total_ask_value > 0 else float('inf')

    # Example: Find large walls (simplified: check within a price % range)
    # Need to adjust threshold based on coin price and config
    current_price = (bids['price'][0] + asks['price'][0]) / 2 # Mid price
    bid_wall_threshold_usd = ORDERBOOK_WALL_THRESHOLD_BTC * current_price # Convert BTC threshold to USD value

    large_bid_wall = bids[bids['amount'] * bids['price'] > bid_wall_threshold_usd].head(1)
    large_ask_wall = asks[asks['amount'] * asks['price'] > bid_wall_threshold_usd].head(1)


    orderbook_analysis = {
        'imbalance_ratio': imbalance_ratio,
        'large_bid_wall': large_bid_wall.to_dict('records')[0] if not large_bid_wall.empty else None,
        'large_ask_wall': large_ask_wall.to_dict('records')[0] if not large_ask_wall.empty else None,
        # Add more orderbook analysis here (spoofing detection, etc.)
    }
    return orderbook_analysis


# --- Symbol Analyzer Class for Realtime Data ---

class SymbolAnalyzer:
    def __init__(self, symbol, interval, candle_limit, orderbook_limit, source='binance'):
        self.symbol = symbol
        self.interval = interval
        self.candle_limit = candle_limit
        self.orderbook_limit = orderbook_limit
        self.source = source
        self.candles_df = pd.DataFrame()
        self.orderbook_snapshot = {'bids': [], 'asks': []} # Store current orderbook state
        self.last_analyzed_candle_time = None # Để tránh phân tích trùng lặp trên cùng 1 nến

        # Fetch initial historical data
        self.fetch_initial_data()

    def fetch_initial_data(self):
        """Fetch historical candles and initial orderbook snapshot."""
        logging.info(f"Fetching initial data for {self.symbol} from {self.source}...")
        # Fetch candles
        try:
            if self.source == 'binance':
                klines = binance_client.get_historical_klines(self.symbol, self.interval, limit=self.candle_limit)
                candles = [{
                    'time': int(k[0]), 'open': float(k[1]), 'high': float(k[2]),
                    'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5]),
                    'close_time': int(k[6]), 'is_closed': k[8]
                } for k in klines]
            # elif self.source == 'kucoin': ... # Add Kucoin fetch if needed
            else:
                 logging.error(f"Unsupported source for initial fetch: {self.source}")
                 return

            self.candles_df = pd.DataFrame(candles)
            if not self.candles_df.empty:
                self.candles_df['time'] = pd.to_datetime(self.candles_df['time'], unit='ms')
                self.candles_df.set_index('time', inplace=True)
                # Set last analyzed time to the last closed candle
                last_closed_candle = self.candles_df[self.candles_df['is_closed'] == True].index.max()
                if last_closed_candle is not pd.NaT:
                     self.last_analyzed_candle_time = last_closed_candle
                logging.info(f"Fetched {len(self.candles_df)} historical candles for {self.symbol}")

        except Exception as e:
            logging.error(f"Error fetching initial candles for {self.symbol}: {e}")

        # Fetch initial orderbook snapshot
        try:
            if self.source == 'binance':
                depth = binance_client.get_order_book(symbol=self.symbol, limit=self.orderbook_limit)
                self.orderbook_snapshot = depth
                logging.info(f"Fetched initial orderbook for {self.symbol}")
            # elif self.source == 'kucoin': ... # Add Kucoin fetch if needed
        except Exception as e:
             logging.error(f"Error fetching initial orderbook for {self.symbol}: {e}")


    def update_kline(self, kline_data):
        """Update candle data with new kline event from WebSocket."""
        # kline_data is the 'k' dictionary from Binance kline stream
        event_time = pd.to_datetime(kline_data['t'], unit='ms')
        is_final = kline_data['x'] # True if candle is closed

        new_candle_data = {
            'time': event_time,
            'open': float(kline_data['o']),
            'high': float(kline_data['h']),
            'low': float(kline_data['l']),
            'close': float(kline_data['c']),
            'volume': float(kline_data['v']),
            'close_time': int(kline_data['T']),
            'is_closed': is_final
        }

        # Check if we're updating the last candle or adding a new one
        if not self.candles_df.empty and self.candles_df.index[-1] == event_time:
            # Update the last candle
            for key, value in new_candle_data.items():
                if key != 'time': # Don't update index
                    self.candles_df.loc[event_time, key] = value
            # logging.debug(f"Updated last candle for {self.symbol}")
        else:
            # Add a new candle
            new_df = pd.DataFrame([new_candle_data]).set_index('time')
            self.candles_df = pd.concat([self.candles_df, new_df]).tail(self.candle_limit)
            # logging.debug(f"Added new candle for {self.symbol}")


        # Trigger analysis if the candle is closed and not analyzed yet
        if is_final and (self.last_analyzed_candle_time is None or event_time > self.last_analyzed_candle_time):
             logging.info(f"Closed candle received for {self.symbol} at {event_time}. Analyzing...")
             self.last_analyzed_candle_time = event_time
             return self.run_analysis() # Run analysis and return signals
        # elif not is_final:
             # Optionally analyze on tick for certain strategies
             # return self.run_analysis(on_tick=True)


        return None # No signal generated from this update

    def update_orderbook(self, orderbook_delta):
        """Update orderbook snapshot with delta event from WebSocket."""
        # orderbook_delta is the dictionary from Binance depth stream
        # Need to implement logic to apply delta (updates and deletions)
        # This is a simplified placeholder. Real implementation needs full orderbook snapshot and delta application.
        # Refer to Binance API docs for how to manage local orderbook state via stream.
        logging.debug(f"Orderbook delta received for {self.symbol}. Needs full implementation.")
        # For simplicity in this example, we'll just re-fetch snapshot on delta (INEFFICIENT)
        # In production, manage the local orderbook state correctly
        # self.orderbook_snapshot = fetch_orderbook(self.symbol, self.orderbook_limit, self.source) # NOT IDEAL

        # Or, simply run analysis on the current snapshot + latest kline if needed
        # This depends on your strategy: do you analyze orderbook on every price tick or only on candle close?
        # return self.run_analysis() # Example: analyze on every orderbook update (might be too frequent)
        return None # By default, don't analyze on every orderbook delta

    def detect_candlestick_patterns(self, data):
        """Nhận diện các mẫu hình nến cơ bản cho nến cuối cùng."""
        patterns = []
        if data.empty or len(data) < 2: # Cần ít nhất 1 nến để phân tích mẫu hình của nến cuối
            return patterns

        # Lấy nến cuối cùng và nến trước đó
        last_candle = data.iloc[-1]
        # prev_candle = data.iloc[-2] # Có thể cần nến trước đó cho một số mẫu hình

        open_p = last_candle['open']
        close_p = last_candle['close']
        high_p = last_candle['high']
        low_p = last_candle['low']

        body = abs(close_p - open_p)
        range_ = high_p - low_p

        # --- Nhận diện mẫu hình cơ bản ---

        # Doji: open và close rất gần nhau, bóng nến trên và dưới tương đối dài
        # Điều kiện đơn giản: thân nến nhỏ hơn 10% tổng range và range > 2 * body
        if range_ > 0 and body < 0.1 * range_ and range_ > 2 * body:
             patterns.append('Doji')

        # Hammer/Hanging Man: Thân nến nhỏ ở phía trên/dưới, bóng dưới dài gấp đôi thân nến
        # Hammer (trong xu hướng giảm): thân nến nhỏ ở phía trên, bóng dưới dài
        # Hanging Man (trong xu hướng tăng): thân nến nhỏ ở phía trên, bóng dưới dài
        # simplified check: small body, lower shadow >= 2 * body
        lower_shadow = min(open_p, close_p) - low_p
        upper_shadow = high_p - max(open_p, close_p)
        if body < 0.2 * range_ and lower_shadow >= 2 * body:
            # Có thể phân biệt Hammer/Hanging Man dựa vào xu hướng trước đó, nhưng ở đây chỉ nhận diện hình dạng nến
            patterns.append('Hammer/Hanging Man')

        # Thêm các mẫu hình khác tại đây (Engulfing, Morning Star, etc.)
        # Cần thêm logic để so sánh với nến trước đó cho nhiều mẫu hình.

        return patterns

    def run_analysis(self, on_tick=False):
        """Run analysis on current data and generate signal message if conditions met."""
        if self.candles_df.empty:
            logging.warning(f"No candle data for analysis on {self.symbol}")
            return None

        # Use a copy to avoid modifying the main data store during analysis
        current_candles = self.candles_df.copy()

        # --- Analyze Price Action (Replicate Pine Script) ---
        price_analysis_df = self.candles_df.copy() # Use the full history for indicator calculation
        price_analysis_df['RSI'] = calculate_rsi(price_analysis_df, 14)
        price_analysis_df['body'] = calculate_body(price_analysis_df)
        price_analysis_df['body_sma'] = calculate_sma(price_analysis_df, 20)

        # Get latest bar's price signals
        latest_bar = price_analysis_df.iloc[-1]
        rsi_overbought = latest_bar['RSI'] > 70
        rsi_oversold = latest_bar['RSI'] < 30
        body_spike_up = (latest_bar['close'] > latest_bar['open']) and (latest_bar['body'] > latest_bar['body_sma'] * 2)
        body_spike_down = (latest_bar['close'] < latest_bar['open']) and (latest_bar['body'] > latest_bar['body_sma'] * 2)

        # Add other signals from Pine Script logic here (Volume Spike, ATR, MSB, OB...)
        # This requires implementing those calculations and logic in Python


        # --- Analyze Orderbook ---
        orderbook_analysis_result = analyze_orderbook_snapshot(self.orderbook_snapshot)

        # --- Combine Signals & Generate Message ---
        signal_message = None
        signals_detected = []

        # Example Combined Logic: Bullish signal if RSI oversold AND large bid wall
        if rsi_oversold and orderbook_analysis_result and orderbook_analysis_result.get('large_bid_wall'):
            signals_detected.append("Bullish: RSI Oversold + Large Bid Wall")

        # Example Combined Logic: Bearish signal if RSI overbought AND large ask wall
        if rsi_overbought and orderbook_analysis_result and orderbook_analysis_result.get('large_ask_wall'):
             signals_detected.append("Bearish: RSI Overbought + Large Ask Wall")

        # Example: Simple Body Spike UP
        if body_spike_up:
             signals_detected.append("Bullish: Body Spike Up")

        # Example: Simple Body Spike DOWN
        if body_spike_down:
             signals_detected.append("Bearish: Body Spike Down")


        # Add more complex combined logic here based on your Pine Script and orderbook analysis needs

        if signals_detected:
            message_parts = [f"⚡️ **Tín hiệu cho {self.symbol} ({self.interval})** ⚡️"]
            message_parts.extend(signals_detected)
            # Optionally add more details
            if orderbook_analysis_result:
                 message_parts.append(f"Orderbook Imbalance: {orderbook_analysis_result.get('imbalance_ratio', 'N/A'):.2f}")
                 # Add wall details if present
                 if orderbook_analysis_result.get('large_bid_wall'):
                      wall = orderbook_analysis_result['large_bid_wall']
                      message_parts.append(f"Large Bid Wall: {wall['amount']:.2f} @ {wall['price']}")
                 if orderbook_analysis_result.get('large_ask_wall'):
                      wall = orderbook_analysis_result['large_ask_wall']
                      message_parts.append(f"Large Ask Wall: {wall['amount']:.2f} @ {wall['price']}")

            # Add latest indicator values
            message_parts.append(f"Latest RSI: {latest_bar.get('RSI', 'N/A'):.2f}")
            message_parts.append(f"Candle: O={latest_bar['open']:.4f} H={latest_bar['high']:.4f} L={latest_bar['low']:.4f} C={latest_bar['close']:.4f}")
            message_parts.append(f"Timestamp: {latest_bar.name}") # Using pandas Timestamp

            signal_message = "\n".join(message_parts)
            logging.info(f"Generated signal for {self.symbol}: {signal_message}")

        # Phân tích mẫu hình nến
        candlestick_patterns = self.detect_candlestick_patterns(current_candles)

        analysis_results = {
            'symbol': self.symbol,
            'source': self.source,
            'timestamp': int(time.time() * 1000),
            'latest_price_signals': latest_signals,
            'orderbook_analysis': orderbook_analysis,
            'candlestick_patterns': candlestick_patterns,
        }

        # Logic tạo tín hiệu
        signal_message = None
        # Ví dụ: Tạo tín hiệu nếu có Doji và RSI oversold
        if 'Doji' in candlestick_patterns and latest_signals.get('RSI_Oversold', False):
             signal_message = f"[{self.symbol}] Tín hiệu tiềm năng: Doji xuất hiện trong vùng RSI Oversold."

        # Thêm các logic tạo tín hiệu khác dựa trên các phân tích

        if signal_message:
            # Trả về kết quả phân tích đầy đủ cùng với tín hiệu
            return analysis_results
        else:
             # Trả về kết quả phân tích mà không có tín hiệu cụ thể
             # Bạn có thể chọn không trả về gì nếu không có tín hiệu, hoặc trả về kết quả phân tích raw
            return analysis_results # Tạm thời trả về kết quả phân tích kể cả khi không có tín hiệu

# Hàm get_combined_analysis cũ (dùng cho lệnh /analyze) vẫn giữ lại
def get_combined_analysis(symbol, interval, limit, orderbook_limit, source='binance'):
    """Kết hợp phân tích giá và orderbook (snapshot request)."""
    logging.info(f"Running snapshot analysis for {symbol} from {source}...")
    # Tái sử dụng logic từ SymbolAnalyzer nhưng chỉ cho 1 lần fetch
    analyzer = SymbolAnalyzer(symbol, interval, limit, orderbook_limit, source)
    # Chạy phân tích trên data vừa fetch (lấy tín hiệu của nến cuối cùng)
    # Note: This might analyze an incomplete current candle
    return {
        "symbol": symbol,
        "source": source,
        "latest_price_signals": analyzer.analyze_price_action(analyzer.candles_df.copy()).to_dict() if not analyzer.candles_df.empty else None, # Use the function from SymbolAnalyzer implicitly
        "orderbook_analysis": analyze_orderbook_snapshot(analyzer.orderbook_snapshot), # Call the standalone function
        "timestamp": int(time.time() * 1000)
    }

# Note: Các hàm calculate_... và analyze_orderbook_snapshot được dùng nội bộ trong SymbolAnalyzer.
# Hàm get_combined_analysis được giữ lại cho lệnh /analyze.

if __name__ == '__main__':
    # Example usage:
    analysis = get_combined_analysis("BTCUSDT", "1m", 500, 20, "binance")
    import json
    print(json.dumps(analysis, indent=2)) 