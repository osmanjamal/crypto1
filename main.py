import json
from flask import Flask, request, render_template, redirect, url_for, flash
import os
import importlib
import concurrent.futures as cf
import datetime
import config
import time as t
import pandas as pd
from binance.client import Client
from binance.enums import *

# تهيئة العميل
binance_client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET)

app = Flask(__name__)
app.config['SECRET_KEY'] = '123fdsgcsfgxgfg1514cgcd45'

@app.route("/webhook", methods=["POST"])
def webhook_user():
    output = []
    print(str(request.data))    
    output.append(str(request.data))
    data = json.loads(request.data)
    output.append("-------------------------------------------------------------------------")
    output.append(f"-------------------  WEBHOOK USER REQUEST  ----------------------------")
    output.append("-------------------------------------------------------------------------")
    try:
        dt = datetime.datetime.now()
        signal_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        output.append(f'| Signal Time : {signal_time}')
    except Exception as e:
        output.append(str(e))
        print(e)
    print_dict_data(data, output)
    print("-------------------------------------------------------------------------")

    with cf.ThreadPoolExecutor(max_workers=2 * os.cpu_count()) as executor:
        future = executor.submit(binance_function, data, output)

    return "Request Processed"

def binance_function(data, output):
    """وظيفة معالجة أوامر التداول في بينانس"""
    try:
        ACTION = data["action"].upper()
        SYMBOL = data["symbol"]
        QTY = float(data["qty"])
        
        try:
            tp = float(data["tp"])
        except:
            tp = 0
        try:
            sl = float(data["sl"])
        except:
            sl = 0   
        
        market_position = data["market_position"].lower()
        
        # التحقق من نوع الحساب (فيوتشر أو سبوت)
        is_futures = SYMBOL.endswith(('USDT', 'BUSD'))
        
        if is_futures:
            # معالجة أوامر الفيوتشر
            if ACTION == "BUY":
                if market_position == "long":
                    # إغلاق المراكز المفتوحة أولاً
                    close_futures_positions(SYMBOL, 'SELL')
                    # فتح مركز شراء جديد
                    order_response = place_futures_order(SYMBOL, 'BUY', QTY, tp, sl)
                elif market_position == "flat":
                    close_futures_positions(SYMBOL, 'SELL')
                    
            elif ACTION == "SELL":
                if market_position == "short":
                    close_futures_positions(SYMBOL, 'BUY')
                    order_response = place_futures_order(SYMBOL, 'SELL', QTY, tp, sl)
                elif market_position == "flat":
                    close_futures_positions(SYMBOL, 'BUY')
                    
        else:
            # معالجة أوامر السبوت
            if ACTION == "BUY":
                if market_position == "long":
                    order_response = place_spot_order(SYMBOL, 'BUY', QTY, tp, sl)
            elif ACTION == "SELL":
                if market_position == "short":
                    order_response = place_spot_order(SYMBOL, 'SELL', QTY, tp, sl)
        
        # تسجيل تفاصيل الأمر
        output.append("--------------------------------------------------------------")
        output.append("------------------   ORDER DETAILS   -------------------------")
        output.append("--------------------------------------------------------------")
        
        dt = datetime.datetime.now()
        order_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        
        if order_response:
            write_signal_data(order_time, ACTION, SYMBOL, data.get('price', 0), tp, sl, QTY, 'binance')
            output.append(
                f"| Order Time: {order_time}\n| Side: {ACTION}\n| Symbol: {SYMBOL}\n| Quantity: {QTY}\n| TP: {tp}\n| SL: {sl}"
            )
            
    except Exception as e:
        print(f"Error in binance_function: {str(e)}")
        output.append(f"Error: {str(e)}")
        
    write_output(output)
    return {"code": "success", "message": "order executed"}

def place_futures_order(symbol, side, quantity, tp=None, sl=None):
    """تنفيذ أمر في سوق العقود المستقبلية"""
    try:
        # تعيين الرافعة المالية
        binance_client.futures_change_leverage(symbol=symbol, leverage=config.LEVERAGE)
        
        # الأمر الأساسي
        order = binance_client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        
        # إضافة وقف الخسارة وجني الأرباح
        if tp and sl:
            if side == 'BUY':
                # وقف الخسارة للشراء
                binance_client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='STOP_MARKET',
                    stopPrice=sl,
                    closePosition=True
                )
                # جني الأرباح للشراء
                binance_client.futures_create_order(
                    symbol=symbol,
                    side='SELL',
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp,
                    closePosition=True
                )
            else:
                # وقف الخسارة للبيع
                binance_client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='STOP_MARKET',
                    stopPrice=sl,
                    closePosition=True
                )
                # جني الأرباح للبيع
                binance_client.futures_create_order(
                    symbol=symbol,
                    side='BUY',
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=tp,
                    closePosition=True
                )
                
        return order
    except Exception as e:
        print(f"Error in place_futures_order: {str(e)}")
        return None

def place_spot_order(symbol, side, quantity, tp=None, sl=None):
    """تنفيذ أمر في السوق الفوري"""
    try:
        # الأمر الأساسي
        order = binance_client.create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        
        # إضافة وقف الخسارة وجني الأرباح للسوق الفوري
        if tp and sl:
            if side == 'BUY':
                binance_client.create_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=tp
                )
                binance_client.create_order(
                    symbol=symbol,
                    side='SELL',
                    type='STOP_LOSS_LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=sl,
                    stopPrice=sl
                )
        return order
    except Exception as e:
        print(f"Error in place_spot_order: {str(e)}")
        return None

def close_futures_positions(symbol, side):
    """إغلاق المراكز المفتوحة في العقود المستقبلية"""
    try:
        positions = binance_client.futures_position_information(symbol=symbol)
        for position in positions:
            if float(position['positionAmt']) != 0:
                binance_client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=abs(float(position['positionAmt'])),
                    reduceOnly=True
                )
    except Exception as e:
        print(f"Error in close_futures_positions: {str(e)}")

def write_signal_data(order_time, action, symbol, price, tp, sl, qty, qty_type):
    """تسجيل بيانات الإشارة"""
    try:
        with open('signals.json', 'r') as f:
            trade_data = json.load(f)
    except FileNotFoundError:
        trade_data = []
    
    trade_data.append({
        'order_time': order_time,
        'action': action,
        'symbol': symbol,
        'entry': price,
        'tp': tp,
        'sl': sl,
        'qty': qty,
        'qty_type': qty_type
    })

    with open('signals.json', 'w') as f:
        json.dump(trade_data, f, indent=4)

def write_output(output):
    """كتابة السجلات في ملف النصوص"""
    with open("output.txt", "a", encoding="utf-8") as output_file:
        for line in output:
            output_file.write(line + "\n")

def print_dict_data(data, output):
    """طباعة بيانات القاموس"""
    for key, value in data.items():
        output.append(f"{key} : {value}")

# الطرق الأخرى تبقى كما هي...

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)