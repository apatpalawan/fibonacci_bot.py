import os
import time
import requests
import pandas as pd
import ta
import yfinance as yf

# 1. ดึงรหัสกุญแจระบบ LINE OA จากระบบคลาวด์ (ตู้ perfect-integrity)
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

def send_line_message(text_msg):
    if not LINE_ACCESS_TOKEN or not LINE_USER_ID:
        print("⚠️ ยังไม่ได้ตั้งค่า LINE_ACCESS_TOKEN หรือ LINE_USER_ID บนระบบคลาวด์ใหม่")
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

# 2. รายชื่อสินทรัพย์เฝ้าระวัง (9 สินทรัพย์ระดับโลก + 15 หุ้นไทย)
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

def scan_fibonacci_markets():
    now_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"🔄 [FIBO BOT] เริ่มรอบสแกนล่าสัดส่วนทองคำ ณ เวลา: {now_str}")
    
    # ---------------- [ ส่วนที่ 1: สแกน สินทรัพย์โลก (Forex & Gold) ] ----------------
    for name, ticker in global_assets.items():
        try:
            # 1. ดึงข้อมูล D1 ย้อนหลังเพื่อคำนวณแนว Fibonacci ของวันก่อนหน้า
            df_d1 = yf.download(ticker, period="5d", interval="1d", progress=False)
            if len(df_d1) < 2: continue
            
            # ใช้ค่า High/Low ของแท่งเมื่อวาน (แท่งก่อนหน้าล่าสุด) เป็นเกณฑ์กางฟีโบ
            prev_high = float(df_d1["High"].squeeze().iloc[-2])
            prev_low = float(df_d1["Low"].squeeze().iloc[-2])
            diff = prev_high - prev_low
            
            # คำนวณแนวรับคำนวณจากบนลงล่าง (สำหรับขาปรับฐานย่อตัว)
            fibo_382 = prev_high - (diff * 0.382)
            fibo_500 = prev_high - (diff * 0.500)
            fibo_618 = prev_high - (diff * 0.618) # ระดับ Golden Ratio 🎯
            
            # 2. ดึงข้อมูล 1H ตรวจสอบราคาปัจจุบันว่าทดสอบแนว Fibo หรือไม่
            df_1h = yf.download(ticker, period="5d", interval="1h", progress=False)
            if len(df_1h) < 25: continue
            
            close_1h = df_1h["Close"].squeeze()
            high_1h = df_1h["High"].squeeze()
            low_1h = df_1h["Low"].squeeze()
            
            current_price = float(close_1h.iloc[-1])
            c_high = float(high_1h.iloc[-1])
            c_low = float(low_1h.iloc[-1])
            
            adx_series = ta.trend.adx(high_1h, low_1h, close_1h, window=14)
            current_adx = float(adx_series.iloc[-1])
            
            if "JPY=X" in ticker or "GC=F" in ticker:
                price_str = f"{current_price:,.2f}"
            else:
                price_str = f"{current_price:.4f}"
                
            # ตรวจสอบว่าแท่งเทียน 1H ล่าสุดวิ่งชนหรือครอบคลุมแนว Fibo หรือไม่
            hit_level = None
            if c_low <= fibo_618 <= c_high:
                hit_level = "Golden Ratio 61.8%"
            elif c_low <= fibo_500 <= c_high:
                hit_level = "Psychology Level 50.0%"
            elif c_low <= fibo_382 <= c_high:
                hit_level = "Strong Trend Level 38.2%"
                
            # 3. ส่งสัญญาณเข้า LINE คัดกรอบ Header แยกสไตล์ชัดเจน
            if hit_level and current_adx > 25:
                send_line_message(
                    f"🎯 [FIBO RETRACE] 🏆 {name}\n"
                    f"🔥 สัญญาณความได้เปรียบ: แท่งราคา 1H วิ่งชนแนวรับ-แนวต้านระดับวัน!\n"
                    f"📊 ระดับแนวที่ทดสอบ: {hit_level}\n"
                    f"📈 แรงส่งตลาด ADX: {current_adx:.1f}\n"
                    f"💵 ราคาปัจจุบัน: {price_str}\n"
                    f"👀 พี่พิจารณากางกราฟดูจังหวะ Action แท่งเทียนเพื่อเข้าออร์เดอร์ได้เลยครับ!"
                )
        except Exception as e:
            print(f"ขัดข้องที่ระบบสแกน Fibo {name}: {e}")

    # ---------------- [ ส่วนที่ 2: สแกน หุ้นไทยรายตัว 15 ตัว ] ----------------
    for ticker in thai_stocks:
        try:
            df_d1 = yf.download(ticker, period="5d", interval="1d", progress=False)
            if len(df_d1) < 2: continue
            
            prev_high = float(df_d1["High"].squeeze().iloc[-2])
            prev_low = float(df_d1["Low"].squeeze().iloc[-2])
            diff = prev_high - prev_low
            
            fibo_618 = prev_high - (diff * 0.618)
            fibo_500 = prev_high - (diff * 0.500)
            
            df_1h = yf.download(ticker, period="5d", interval="1h", progress=False)
            if len(df_1h) < 10: continue
            
            c_high = float(df_1h["High"].squeeze().iloc[-1])
            c_low = float(df_1h["Low"].squeeze().iloc[-1])
            current_price = float(df_1h["Close"].squeeze().iloc[-1])
            stock_name = ticker.replace(".BK", "")
            
            hit_level = None
            if c_low <= fibo_618 <= c_high:
                hit_level = "Golden Ratio 61.8%"
            elif c_low <= fibo_500 <= c_high:
                hit_level = "Level 50.0%"
                
            if hit_level:
                send_line_message(
                    f"🎯 [FIBO STOCK] 🏆 {stock_name}\n"
                    f"🔥 ราคาหุ้นวิ่งลงมาทดสอบแนวรับ Fibonacci ของเมื่อวาน!\n"
                    f"📊 ระดับแนวที่เจอ: {hit_level}\n"
                    f"💵 ราคาหุ้นปัจจุบัน: {current_price:.2f} บาท\n"
                    f"💡 เหมาะสำหรับพิจารณาหาจังหวะรับของเทรด DW ครับพี่!"
                )
        except Exception as e:
            print(f"ขัดข้องที่ระบบ Fibo หุ้นไทย {ticker}: {e}")

if __name__ == "__main__":
    print("🤖 บอทเรดาร์คลาวด์กลยุทธ์ Fibonacci ล่าระดับทองคำ เริ่มทำงาน...")
    send_line_message("☁️ [FIBO BOT] สแตนบายบนตู้ใหม่เรียบร้อย! ระบบแยกสแกนหาระยะย่อทองคำ 38.2%/50%/61.8% ออนไลน์พร้อมแจงสัญญาณเตือนให้พี่พิจารณาแล้วครับ!")
    while True:
        scan_fibonacci_markets()
        time.sleep(3600) # ทำงานสแกนทุก ๆ 1 ชั่วโมง