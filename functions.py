from flask import Flask, request, render_template, redirect, url_for,flash
import json
from binance.client import Client
from binance.enums import *
import datetime
import math
import asyncio
from typing import Dict, List, Any
from config import Config

def ip_address():
    if 'X-Forwarded-For' in request.headers:
        proxy_data = request.headers['X-Forwarded-For']
        ip_list = proxy_data.split(',')
        user_ip = ip_list[0]
        user_ip = user_ip.replace(".", "")
    else:
        user_ip = request.remote_addr
        user_ip = user_ip.replace(".", "")
    return user_ip

def tg_token():
    token = fetch_database('t_bot_token.json')
    token = token['bot_token']
    return token

def tg_channel():
    channel = fetch_database('t_bot_channel.json')
    channel = channel['channel']
    return channel

def fetch_database(db_name):
    try:
        read_data = database_read(db_name)
        data = read_data.replace("'", '"')
        data = json.loads(data)
        return data
    except Exception as e: 
        print(e)

def database_read(file_name):
    with open(file_name, "r+") as sincefile:
        since_date = sincefile.read()
    return since_date

def fetch_pos_data(client, symbol):
    """الحصول على بيانات المركز المفتوح"""
    try:
        positions = client.futures_position_information(symbol=symbol)
        for position in positions:
            if float(position['positionAmt']) != 0:  # مركز مفتوح
                return {
                    'quantity': abs(float(position['positionAmt'])),
                    'entry_price': float(position['entryPrice']),
                    'side': 'BUY' if float(position['positionAmt']) > 0 else 'SELL'
                }
        return None
    except Exception as e:
        print(f"خطأ في fetch_pos_data: {str(e)}")
        return None

def write_signal_data(order_time, action, symbol, price, tp, sl, qty, qty_type):
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

def write_trade_data(order_id, order_time, action, symbol, price, qty):
    try:
        with open('trades.json', 'r') as f:
            trade_data = json.load(f)
    except FileNotFoundError:
        trade_data = []
    
    trade_data.append({
        'order_time': order_time,
        'order_id': order_id,
        'action': action,
        'symbol': symbol,
        'price': price,
        'qty': qty
    })

    with open('trades.json', 'w') as f:
        json.dump(trade_data, f, indent=4)

def delete_duplicates_with_symbol(trade_data, symbol):
    unique_data = []
    symbol_found = False

    for trade in trade_data:
        if trade.get('symbol') == symbol:
            if not symbol_found:
                symbol_found = True
                unique_data.append(trade)
        else:
            unique_data.append(trade)

    return unique_data

def read(file_name):
    with open(file_name, "r+") as file:
        read_file = file.read()
    return read_file

def write(file_name, data):
    with open(file_name, "w") as file:
        file.write(str(data))

def truncate_float(number):
    number_str = str(number)
    integer_part, decimal_part = number_str.split('.')
    truncated_decimal = decimal_part[:2]
    truncated_str = f"{integer_part}.{truncated_decimal}"
    return float(truncated_str)

def print_dict_data(data, output):
    for key, value in data.items():
        output.append(f"{key} : {value}")

def log_value(value):
    with open('max_loss.txt', 'a') as file:
        file.write(f'{value}\n')

def check_trade():
    trade = True
    consecutive_negative = 0
    with open('max_loss.txt', 'r') as file:
        for line in file:
            value = float(line.strip())
            if value < 0:
                consecutive_negative += 1
                max_consecutive_loss = read('max_loss_value.txt')
                if max_consecutive_loss != '':
                    if consecutive_negative == float(max_consecutive_loss):
                        trade = False
                        return trade
            else:
                consecutive_negative = 0
    return trade

def update_config(index_1, value_1, index_2, value_2, index_3, value_3):
    with open('config.py', 'r') as file:
        lines = file.readlines()

    modified_lines = []
    for line in lines:
        if line.startswith(index_1):
            modified_lines.append(f"{index_1}'{value_1}'\n")
        elif line.startswith(index_2):
            modified_lines.append(f"{index_2}'{value_2}'\n")
        elif line.startswith(index_3):
            modified_lines.append(f"{index_3}'{value_3}'\n")
        else:
            modified_lines.append(line)
    
    with open('config.py', 'w') as file:
        file.writelines(modified_lines)
    print('تم تحديث بيانات API بنجاح')

def update_telegram(tg_token, tg_channel):
    with open('config.py', 'r') as file:
        lines = file.readlines()
  
    modified_lines = []
    for line in lines:
        if line.startswith('tg_token = '):
            modified_lines.append(f"tg_token = '{tg_token}'\n")
        elif line.startswith('tg_channel = '):
            modified_lines.append(f"tg_channel = '{tg_channel}'\n")
        else:
            modified_lines.append(line)
    
    with open('config.py', 'w') as file:
        file.writelines(modified_lines)
    print('تم تحديث بيانات التيليجرام بنجاح')

def close_positions_by_symbol(client, action, symbol, output):
    """إغلاق المراكز المفتوحة"""
    try:
        positions = client.futures_position_information(symbol=symbol)
        volume = 0
        for position in positions:
            if float(position['positionAmt']) != 0:  # مركز مفتوح
                side = 'SELL' if float(position['positionAmt']) > 0 else 'BUY'
                if (action == 'BUY' and side == 'SELL') or (action == 'SELL' and side == 'BUY'):
                    quantity = abs(float(position['positionAmt']))
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=side,
                        type='MARKET',
                        quantity=quantity,
                        reduceOnly=True
                    )
                    volume = quantity
                    output.append(f"تم إغلاق مركز {symbol} بكمية {quantity}")
        return volume
    except Exception as e:
        output.append(f"خطأ في إغلاق المراكز: {str(e)}")
        return 0

def place_order(client, action, symbol, volume, price, tp=None, sl=None, output=None):
    """تنفيذ أمر جديد"""
    try:
        # تحديد نوع السوق (فيوتشر أو سبوت)
        is_futures = symbol.endswith(('USDT', 'BUSD'))
        
        if is_futures:
            # تغيير الرافعة المالية إذا كان ضرورياً
            client.futures_change_leverage(symbol=symbol, leverage=10)
            
            # الأمر الأساسي
            order = client.futures_create_order(
                symbol=symbol,
                side=action,
                type='MARKET',
                quantity=volume
            )
            
            # إضافة TP & SL
            if tp or sl:
                opposite_side = 'SELL' if action == 'BUY' else 'BUY'
                if tp:
                    client.futures_create_order(
                        symbol=symbol,
                        side=opposite_side,
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp,
                        closePosition=True
                    )
                if sl:
                    client.futures_create_order(
                        symbol=symbol,
                        side=opposite_side,
                        type='STOP_MARKET',
                        stopPrice=sl,
                        closePosition=True
                    )
        else:
            # أمر سبوت
            order = client.create_order(
                symbol=symbol,
                side=action,
                type='MARKET',
                quantity=volume
            )
            
        if output:
            output.append(f"تم تنفيذ أمر {action} لـ {symbol} بكمية {volume}")
        return order
    except Exception as e:
        if output:
            output.append(f"خطأ في تنفيذ الأمر: {str(e)}")
        return None

class TradingActions:
    def __init__(self, client, action, symbol, qty, price, tp, sl, which_account, output):
        self.client = client
        self.action = action
        self.symbol = symbol
        self.qty = qty
        self.price = price
        self.tp = tp
        self.sl = sl
        self.which_account = which_account
        self.output = output if output else []
        self.order_response = None

    def execute_action(self, market_position):
        """تنفيذ إجراء التداول"""
        try:
            # إغلاق المراكز الموجودة إذا لزم الأمر
            if market_position != 'flat':
                volume = close_positions_by_symbol(self.client, self.action, self.symbol, self.output)
            
            # فتح مركز جديد إذا كان الاتجاه مناسباً
            if (self.action == "BUY" and market_position == "long") or \
               (self.action == "SELL" and market_position == "short"):
                self.order_response = place_order(
                    self.client, self.action, self.symbol, 
                    abs(self.qty), self.price, self.tp, self.sl, 
                    self.output
                )
            
            self.write_order_details()
        except Exception as e:
            self.output.append(f"خطأ في تنفيذ الإجراء: {str(e)}")

    def write_order_details(self):
        """تسجيل تفاصيل الأمر"""
        try:
            dt = datetime.datetime.now()
            order_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            if self.order_response:
                write_signal_data(
                    order_time, self.action, self.symbol, self.price,
                    self.tp, self.sl, self.qty, self.which_account
                )
                self.output.append(
                    f"| وقت الأمر: {order_time}\n"
                    f"| النوع: {self.action}\n"
                    f"| الزوج: {self.symbol}\n"
                    f"| السعر: {self.price}\n"
                    f"| TP: {self.tp}\n"
                    f"| SL: {self.sl}\n"
                    f"| الكمية: {self.qty}\n"
                    f"| الحساب: {self.which_account}"
                )
        except Exception as e:
            self.output.append(f"خطأ في كتابة تفاصيل الأمر: {str(e)}")
        
        with open("output.txt", "a", encoding="utf-8") as output_file:
            for line in reversed(self.output):
                output_file.write(line + "\n")