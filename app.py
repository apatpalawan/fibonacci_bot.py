import os
import time
import requests
import pandas as pd
import ta
import yfinance as yf

# 1. ดึงรหัสกุญแจระบบ LINE OA จากระบบคลาวด์
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def send_line_message(text_msg):
    if not LINE_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ ยังไม่ได้ตั้งค่า LINE_ACCESS_TOKEN หรือ LINE_USER_ID บนระบบคลาวด์")
        return
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + LINE_ACCESS_TOKEN
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text_msg}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"❌ ส่งไลน์ไม่สำเร็จ: {response.text}")
    except Exception as e:
        print(f"❌ ระบบส่งขัดข้อง: {e}")

# 2. รายชื่อสินทรัพย์เฝ้าระวัง
thai_stocks = [
    "ADVANC.BK", "AOT.BK", "BBL.BK", "BDMS.BK", "CPALL.BK", 
    "DELTA.BK", "KBANK.BK", "PTT.BK", "SCB.BK", "TRUE.BK",
    "BH.BK", "SCC.BK", "CPN.BK", "GULF.BK", "TOP.BK"
]
global_assets = {
    "ทองคำ (Gold)": "GC=F", 
    "EUR/USD (ยูโร)": "EURUSD=X", 
    "GBP/USD (ปอนด์)": "GBPUSD=X", 
    "USD/JPY (เยน)": "USDJPY=X",
    "AUD/USD (ออสซี่)": "AUDUSD=X",
    "USD/CAD (แคนาดา)": "USDCAD=X",
    "USD/CHF (สวิสฟรังก์)": "USDCHF=X",
    "NZD/USD (กีวี่)": "NZDUSD=X",
    "GBP/JPY (จีเจสายซิ่ง)": "GBPJPY=X"
}

def suggest_dw(stock_name, type_cp):
    return f"{stock_name}01{type_cp}2609 หรือ {stock_name}19{type_cp}2609"

# 3. ฟังก์ชันคำนวณจิตวิทยา Price Action จากแท่งเทียน
def check_price_action(open_p, high_p, low_p, close_p, open_prev, close_prev):
    body = abs(close_p - open_p)
    upper_wick = high_p - max(open_p, close_p)
    lower_wick = min(open_p, close_p) - low_p
    
    if close_p > open_p and close_prev < open_prev and close_p > open_prev and open_p < close_prev:
        return "BULLISH_ENGULFING"
    if lower_wick >= (body * 2) and upper_wick <= (body * 0.5) and body > 0:
        return "HAMMER_PINBAR"
    if close_p < open_p and close_prev > open_prev and close_p < open_prev and open_p > close_prev:
        return "BEARISH_ENGULFING"
    if upper_wick >= (body * 2) and lower_wick <= (body * 0.5) and body > 0:
        return "SHOOTING_STAR"
        
    return "NONE"

def scan_markets():
    now_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"🔄 เริ่มรอบสแกนขั้นเทพ V3 (3 ไอเดียรายใหญ่คุม Header) ณ เวลา: {now_str}")
    
    # ---------------- [ พาร์ทพิเศษ: สแกน ดัชนี SET50 ตรง ๆ ] ----------------
    try:
        df_set50 = yf.download("^SET50", period="45d", interval="1d", progress=False)
        if len(df_set50) >= 22:
            close_s50 = df_set50["Close"].squeeze()
            open_s50 = df_set50["Open"].squeeze()
            high_s50 = df_set50["High"].squeeze()
            low_s50 = df_set50["Low"].squeeze()
            volume_s50 = df_set50["Volume"].squeeze()
            
            vol_avg_s50 = volume_s50.shift(1).rolling(window=20).mean()
            vol_ratio_s50 = float(volume_s50.iloc[-1] / vol_avg_s50.iloc[-1])
            
            pa_s50 = check_price_action(
                float(open_s50.iloc[-1]), float(high_s50.iloc[-1]), float(low_s50.iloc[-1]), float(close_s50.iloc[-1]),
                float(open_s50.iloc[-2]), float(close_s50.iloc[-2])
            )
            current_s50 = float(close_s50.iloc[-1])
            
            if vol_ratio_s50 >= 1.5:
                if pa_s50 in ["BULLISH_ENGULFING", "HAMMER_PINBAR"]:
                    send_line_message(f"🟢 [CALL SET50] 🐋 ^SET50\n🚀 สัญญาณดัชนี: โวลุ่มแน่น {vol_ratio_s50:.1f} เท่า + {pa_s50}\n📊 ระดับดัชนี: {current_s50:.2f}")
                elif pa_s50 in ["BEARISH_ENGULFING", "SHOOTING_STAR"]:
                    send_line_message(f"🔴 [PUT SET50] 🌋 ^SET50\n🚨 สัญญาณดัชนี: โวลุ่มเทขาย {vol_ratio_s50:.1f} เท่า + {pa_s50}\n📊 ระดับดัชนี: {current_s50:.2f}")
    except Exception as e:
        print(f"ขัดข้องที่ดัชนี SET50: {e}")

    # ---------------- [ พาร์ทที่ 1: สแกน หุ้นไทยรายตัว 15 ตัว & DW ] ----------------
    for ticker in thai_stocks:
        try:
            df_d1 = yf.download(ticker, period="45d", interval="1d", progress=False)
            if len(df_d1) < 22: continue
            
            close_d1 = df_d1["Close"].squeeze()
            open_d1 = df_d1["Open"].squeeze()
            high_d1 = df_d1["High"].squeeze()
            low_d1 = df_d1["Low"].squeeze()
            volume_d1 = df_d1["Volume"].squeeze()
            
            vol_avg_20d = volume_d1.shift(1).rolling(window=20).mean()
            volume_ratio = float(volume_d1.iloc[-1] / vol_avg_20d.iloc[-1])
            
            pa_d1 = check_price_action(
                float(open_d1.iloc[-1]), float(high_d1.iloc[-1]), float(low_d1.iloc[-1]), float(close_d1.iloc[-1]),
                float(open_d1.iloc[-2]), float(close_d1.iloc[-2])
            )
            
            current_price = float(close_d1.iloc[-1])
            stock_name = ticker.replace(".BK", "")
            
            if volume_ratio >= 2.5:
                if pa_d1 in ["BULLISH_ENGULFING", "HAMMER_PINBAR"]:
                    dw_code = suggest_dw(stock_name, "C")
                    send_line_message(f"🟢 [CALL STOCK] 🐋 {stock_name}\n🚀 วอลลุ่มพุ่ง {volume_ratio:.1f} เท่า + แท่งกลับตัว {pa_d1}\n💵 ราคา: {current_price:.2f}\n💡 DW: {dw_code}")
                elif pa_d1 in ["BEARISH_ENGULFING", "SHOOTING_STAR"]:
                    dw_code = suggest_dw(stock_name, "P")
                    send_line_message(f"🔴 [PUT STOCK] 🌋 {stock_name}\n🚨 วอลลุ่มพุ่ง {volume_ratio:.1f} เท่า + แท่งทุบตัว {pa_d1}\n💵 ราคา: {current_price:.2f}\n💡 DW: {dw_code}")
        except Exception as e:
            print(f"ขัดข้องที่หุ้นไทย {ticker}: {e}")

    # ---------------- [ พาร์ทที่ 2: สแกน Forex & ทองคำ (ระบบรวม 3 ไอเดียขั้นเทพ) ] ----------------
    for name, ticker in global_assets.items():
        try:
            # 1. ดึงข้อมูลกราฟ D1 คำนวณเทรนด์และระบบคะแนน
            df_d1 = yf.download(ticker, period="45d", interval="1d", progress=False)
            if len(df_d1) < 25: continue
            
            close_d1 = df_d1["Close"].squeeze()
            high_d1 = df_d1["High"].squeeze()
            low_d1 = df_d1["Low"].squeeze()
            volume_d1 = df_d1["Volume"].squeeze()
            
            # คำนวณ OBV และค่าเฉลี่ยโวลุ่มรายใหญ่
            obv_series = ta.volume.on_balance_volume(close_d1, volume_d1)
            obv_ema20 = obv_series.ewm(span=20, adjust=False).mean()
            vol_avg_20d = volume_d1.shift(1).rolling(window=20).mean()
            
            current_obv = float(obv_series.iloc[-1])
            current_obv_ema = float(obv_ema20.iloc[-1])
            
            pa_trend_d1 = check_price_action(
                float(df_d1["Open"].squeeze().iloc[-1]), float(high_d1.iloc[-1]), float(low_d1.iloc[-1]), float(close_d1.iloc[-1]),
                float(df_d1["Open"].squeeze().iloc[-2]), float(close_d1.iloc[-2])
            )
            
            # ไอเดียที่ 3: ระบบตรวจจับกับดักรายใหญ่ (Divergence Warning)
            is_bullish_divergence = False
            is_bearish_divergence = False
            
            # เช็คจุดต่ำสุด/สูงสุดย้อนหลังเพื่อหาจุดกลับทาง
            if float(close_d1.iloc[-1]) > float(close_d1.iloc[-5]) and float(obv_series.iloc[-1]) < float(obv_series.iloc[-5]):
                is_bearish_divergence = True # ราคาขึ้นแต่วอลลุ่มลดลง = รายใหญ่หลอกล่อให้ติดดอย
            elif float(close_d1.iloc[-1]) < float(close_d1.iloc[-5]) and float(obv_series.iloc[-1]) > float(obv_series.iloc[-5]):
                is_bullish_divergence = True # ราคาลงแต่วอลลุ่มเพิ่มขึ้น = รายใหญ่แอบเก็บของเงียบ ๆ
            
            # ไอเดียที่ 2: ระบบคำนวณคะแนน Smart Money Score (เต็ม 3 คะแนน)
            sm_score = 0
            d1_direction = "NONE"
            
            if pa_trend_d1 in ["BULLISH_ENGULFING", "HAMMER_PINBAR"]:
                d1_direction = "BUY"
                sm_score += 1
                if current_obv > current_obv_ema: sm_score += 1
                if float(volume_d1.iloc[-1]) > float(vol_avg_20d.iloc[-1]): sm_score += 1
            elif pa_trend_d1 in ["BEARISH_ENGULFING", "SHOOTING_STAR"]:
                d1_direction = "SELL"
                sm_score += 1
                if current_obv < current_obv_ema: sm_score += 1
                if float(volume_d1.iloc[-1]) > float(vol_avg_20d.iloc[-1]): sm_score += 1
                
            if d1_direction == "NONE": continue
            
            # 2. ดึงข้อมูลภาพเล็ก 1H หาจังหวะย่อพักแตะเส้นกลาง BB
            df_1h = yf.download(ticker, period="30d", interval="1h", progress=False)
            if len(df_1h) < 25: continue
            
            close_1h = df_1h["Close"].squeeze()
            high_1h = df_1h["High"].squeeze()
            low_1h = df_1h["Low"].squeeze()
            
            adx_series = ta.trend.adx(high_1h, low_1h, close_1h, window=14)
            bb_indicator = ta.volatility.BollingerBands(close=close_1h, window=20, window_dev=2)
            bb_middle = bb_indicator.bollinger_mavg()
            
            current_adx = float(adx_series.iloc[-1])
            c_high = float(high_1h.iloc[-1])
            c_low = float(low_1h.iloc[-1])
            c_mid = float(bb_middle.iloc[-1])
            current_price = float(close_1h.iloc[-1])
            
            if "JPY=X" in ticker or "GC=F" in ticker:
                price_str = f"{current_price:,.2f}"
            else:
                price_str = f"{current_price:.4f}"
            
            is_touch_middle = (c_high >= c_mid) and (c_low <= c_mid)
            
            # 3. ส่งสัญญาณเข้า LINE คัดกรอบ Header (ไอเดียที่ 1 + 2 + 3)
            if is_touch_middle and current_adx > 25:
                # กรณีเจอ Divergence ดักคอรายใหญ่หลอกลวง (ไอเดียที่ 3)
                if d1_direction == "BUY" and is_bearish_divergence:
                    send_line_message(f"⚠️ [FAKE OUT WARNING!] 🦊 {name}\n🚨 ระวัง! ราคาทำทรงขึ้นแต่โวลุ่มสะสม OBV ลดลงชัดเจน รายใหญ่อาจล่อให้ติดดอย!\n📊 ราคาปัจจุบัน: {price_str} | ADX: {current_adx:.1f}")
                elif d1_direction == "SELL" and is_bullish_divergence:
                    send_line_message(f"⚠️ [FAKE OUT WARNING!] 🦊 {name}\n🚨 ระวัง! ราคาทำทรงดิ่งลงแต่โวลุ่มสะสม OBV ยกตัวขึ้น รายใหญ่อาจแอบเก็บของอยู่เงียบ ๆ!\n📊 ราคาปัจจุบัน: {price_str} | ADX: {current_adx:.1f}")
                
                # กรณีสัญญาณคุณภาพดี ไปตามแผน (ไอเดียที่ 1 + 2)
                else:
                    if d1_direction == "BUY":
                        send_line_message(f"🟢 [BUY NOW] 🐋 {name} | Score: {sm_score}/3\n🎯 เทรนด์ใหญ่: D1 เกิดแท่งกลับตัวขึ้น {pa_trend_d1}\n🔄 จังหวะ 1H: ย่อตัวลงมาแตะเส้นกลาง Bollinger Bands แล้ว\n🔥 ADX มีแรงส่ง: {current_adx:.1f} | ราคา: {price_str}\n👀 พี่พิจารณากดเปิดออร์เดอร์ได้เลยครับ!")
                    elif d1_direction == "SELL":
                        send_line_message(f"🔴 [SELL NOW] 🌋 {name} | Score: {sm_score}/3\n🎯 เทรนด์ใหญ่: D1 เกิดแท่งทุบตัวลง {pa_trend_d1}\n🔄 จังหวะ 1H: รีบาวด์ขึ้นมาแตะเส้นกลาง Bollinger Bands แล้ว\n🔥 ADX มีแรงส่ง: {current_adx:.1f} | ราคา: {price_str}\n👀 พี่พิจารณากดเปิดออร์เดอร์ได้เลยครับ!")
                        
        except Exception as e:
            print(f"ขัดข้องที่ระบบสแกน V3 มหาเทพ {name}: {e}")

if __name__ == "__main__":
    print("🤖 บอทเรดาร์คลาวด์มหาเทพ V3 เริ่มทำงาน...")
    send_line_message("☁️ บอทเรดาร์คลาวด์ มหาเทพ V3 อัปเกรดเรียบร้อย! ระบบคุมสัญญานผ่าน Header สั้นคม + แจกคะแนน Score 3/3 + ตรวจกับดัก Divergence Warning ออนไลน์สมบูรณ์แบบครับพี่!")
    while True:
        scan_markets()
        time.sleep(3600)