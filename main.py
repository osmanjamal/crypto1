from flask import Flask, request, render_template, redirect, url_for, flash
from binance.client import Client
from binance.enums import *
import json
import datetime
import asyncio
from functools import wraps
import os
import concurrent.futures as cf
import pandas as pd

# الملفات المحلية
from config import Config
from functions import (
    write_signal_data,
    close_positions_by_symbol,
    place_order,
    print_dict_data,
    ip_address,
    read,
    write,
    get_account_info,
    get_open_positions
)
# تهيئة التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# تهيئة عميل بينانس
try:
    binance_client = Client(Config.BINANCE_API_KEY, Config.BINANCE_API_SECRET)
except Exception as e:
    print(f"خطأ في تهيئة عميل بينانس: {str(e)}")


def write_output(output: List[str]) -> None:
    """كتابة المخرجات إلى الملف مع تنسيق محسن"""
    try:
        with open("output.txt", "a", encoding="utf-8") as output_file:
            output_file.write("\n" + "="*50 + "\n")
            output_file.write(f"وقت التنفيذ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output_file.write("="*50 + "\n")
            
            for line in output:
                if isinstance(line, str):
                    output_file.write(f"{line}\n")
                else:
                    output_file.write(f"{str(line)}\n")
            
            output_file.write("="*50 + "\n\n")
    except Exception as e:
        print(f"خطأ في كتابة المخرجات: {str(e)}")

def place_futures_order(symbol: str, side: str, quantity: float, tp: float = None, sl: float = None) -> Dict[str, Any]:
    """تنفيذ أمر في سوق العقود المستقبلية"""
    try:
        # تعيين الرافعة المالية
        try:
            binance_client.futures_change_leverage(
                symbol=symbol,
                leverage=Config.LEVERAGE
            )
        except Exception as e:
            print(f"خطأ في تعيين الرافعة المالية: {str(e)}")
            
        # الأمر الأساسي
        order = binance_client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
            
        # إضافة وقف الخسارة وجني الأرباح
        if order and (tp or sl):
            try:
                opposite_side = 'SELL' if side == 'BUY' else 'BUY'
                
                if tp:
                    binance_client.futures_create_order(
                        symbol=symbol,
                        side=opposite_side,
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp,
                        closePosition=True,
                        workingType='MARK_PRICE'
                    )
                
                if sl:
                    binance_client.futures_create_order(
                        symbol=symbol,
                        side=opposite_side,
                        type='STOP_MARKET',
                        stopPrice=sl,
                        closePosition=True,
                        workingType='MARK_PRICE'
                    )
                    
            except Exception as e:
                print(f"خطأ في إضافة TP/SL: {str(e)}")
        
        return order
        
    except Exception as e:
        print(f"خطأ في تنفيذ الأمر: {str(e)}")
        return None
@app.route("/webhook", methods=["POST"])
def webhook_user():
    """معالجة الإشارات الواردة من Webhook"""
    output = []
    try:
        print(str(request.data))    
        output.append(str(request.data))
        data = json.loads(request.data)
        
        output.append("="*70)
        output.append("                      طلب WEBHOOK جديد                        ")
        output.append("="*70)
        
        dt = datetime.datetime.now()
        signal_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        output.append(f'وقت الإشارة: {signal_time}')
        
        print_dict_data(data, output)
        output.append("="*70)

        with cf.ThreadPoolExecutor(max_workers=2 * os.cpu_count()) as executor:
            future = executor.submit(binance_function, data, output)

        return "تم معالجة الطلب"
    except Exception as e:
        output.append(f"خطأ في معالجة الإشارة: {str(e)}")
        write_output(output)
        return "حدث خطأ في المعالجة"

def binance_function(data: Dict[str, Any], output: List[str]) -> Dict[str, str]:
    """معالجة إشارات التداول"""
    try:
        # استخراج بيانات الإشارة
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
        
        market_position = data["market_position"]
        price = float(data.get("price", 0))

        # تسجيل تفاصيل الإشارة
        output.append("\n=== تفاصيل الإشارة ===")
        output.append(f"الزوج: {SYMBOL}")
        output.append(f"العملية: {ACTION}")
        output.append(f"الكمية: {QTY}")
        output.append(f"السعر: {price}")
        output.append(f"الموقف: {market_position}")
        output.append(f"جني الأرباح: {tp}")
        output.append(f"وقف الخسارة: {sl}")

        order_response = None
        
        # تنفيذ استراتيجية التداول
        if ACTION == "BUY":
            if market_position == "long":
                try:
                    # إغلاق المراكز القائمة أولاً
                    close_positions_by_symbol(binance_client, "SELL", SYMBOL, output)
                    # فتح مركز شراء جديد
                    order_response = place_futures_order(SYMBOL, "BUY", QTY, tp, sl)
                except Exception as e:
                    output.append(f"خطأ في تنفيذ أمر الشراء: {str(e)}")
            
            elif market_position == 'flat':
                try:
                    close_positions_by_symbol(binance_client, "SELL", SYMBOL, output)
                except Exception as e:
                    output.append(f"خطأ في إغلاق المراكز: {str(e)}")

        elif ACTION == "SELL":
            if market_position == "short":
                try:
                    close_positions_by_symbol(binance_client, "BUY", SYMBOL, output)
                    order_response = place_futures_order(SYMBOL, "SELL", QTY, tp, sl)
                except Exception as e:
                    output.append(f"خطأ في تنفيذ أمر البيع: {str(e)}")
            
            elif market_position == 'flat':
                try:
                    close_positions_by_symbol(binance_client, "BUY", SYMBOL, output)
                except Exception as e:
                    output.append(f"خطأ في إغلاق المراكز: {str(e)}")

        # تسجيل نتيجة التنفيذ
        output.append("\n=== نتيجة التنفيذ ===")
        order_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if order_response:
            write_signal_data(order_time, ACTION, SYMBOL, price, tp, sl, QTY, "binance")
            output.append(
                f"تم تنفيذ الأمر:\n"
                f"الوقت: {order_time}\n"
                f"النوع: {ACTION}\n"
                f"الزوج: {SYMBOL}\n"
                f"السعر: {price}\n"
                f"TP: {tp}\n"
                f"SL: {sl}\n"
                f"الكمية: {QTY}"
            )
        else:
            output.append("لم يتم تنفيذ أي أمر")
            
    except Exception as e:
        output.append(f"خطأ في معالجة الإشارة: {str(e)}")
    
    write_output(output)
    return {"code": "success", "message": "تم تنفيذ العملية"}

@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    error = ''
    if request.method == 'POST':
        if request.form.get('username') != Config.ADMIN_USERNAME or \
           request.form.get('password') != Config.ADMIN_PASSWORD:
            error = 'بيانات الدخول غير صحيحة'
            flash('بيانات الدخول غير صحيحة، حاول مرة أخرى', 'error')
        else:
            write('auth.txt', 'authenticated')
            write('ip_address.txt', ip_address())
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """تسجيل الخروج"""
    write('auth.txt', 'unauthenticated')
    write('ip_address.txt', '')
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def main():
    """الصفحة الرئيسية"""
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()
    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
async def index():
    """لوحة التحكم"""
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()

    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        script_type = request.form.get('script_type', "")
        quantity = request.form.get('qty', "")
        symbol = request.form.get('symbol', "")
        alert_type = request.form.get('alert_type', "")
        tp_i = request.form.get('tp_distance', "0")
        sl_i = request.form.get('sl_distance', "0")

        syntax = generate_webhook_syntax(script_type, alert_type, symbol, quantity, tp_i, sl_i)
        return render_template('index.html', syntax=syntax)
    
    # الحصول على معلومات الحساب
    try:
        account_info = get_account_info()
        open_positions = get_open_positions()
    except Exception as e:
        account_info = {"error": str(e)}
        open_positions = []
    
    return render_template('index.html', 
                         account_info=account_info,
                         open_positions=open_positions)

@app.route('/signals', methods=['GET', 'POST'])
async def signals():
    """صفحة الإشارات"""
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()
    
    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    
    try:
        with open('signals.json', 'r') as f:
            trade_data = json.load(f)
            df = pd.DataFrame(
                trade_data,
                columns=['order_time', 'symbol', 'action', 'entry', 'qty', 'qty_type']
            )
            df.rename(columns={
                'order_time': 'الوقت',
                'symbol': 'الزوج',
                'action': 'العملية',
                'qty': 'الكمية',
                'entry': 'السعر',
                'qty_type': 'الحساب'
            }, inplace=True)
            df = df.sort_values(by="الوقت", ascending=False)
    except Exception as e:
        df = pd.DataFrame()
        print(f"خطأ في قراءة ملف الإشارات: {str(e)}")

    return render_template('signals.html',
                         tables=[df.to_html(classes='data')],
                         titles=df.columns.values)

def get_account_info() -> Dict[str, Any]:
    """الحصول على معلومات الحساب"""
    try:
        futures_account = binance_client.futures_account_balance()
        total_balance = sum(float(balance['balance']) for balance in futures_account)
        available_balance = sum(float(balance['availableBalance']) for balance in futures_account)
        
        return {
            'total_balance': round(total_balance, 2),
            'available_balance': round(available_balance, 2),
            'currency': 'USDT'
        }
    except Exception as e:
        print(f"خطأ في الحصول على معلومات الحساب: {str(e)}")
        return {}

def get_open_positions() -> List[Dict[str, Any]]:
    """الحصول على المراكز المفتوحة"""
    try:
        positions = binance_client.futures_position_information()
        open_positions = []
        
        for position in positions:
            amt = float(position['positionAmt'])
            if amt != 0:
                open_positions.append({
                    'symbol': position['symbol'],
                    'side': 'LONG' if amt > 0 else 'SHORT',
                    'size': abs(amt),
                    'entry_price': float(position['entryPrice']),
                    'mark_price': float(position['markPrice']),
                    'pnl': float(position['unRealizedProfit'])
                })
        
        return open_positions
    except Exception as e:
        print(f"خطأ في الحصول على المراكز المفتوحة: {str(e)}")
        return []

def generate_webhook_syntax(script_type: str, alert_type: str, symbol: str, 
                          quantity: str, tp: str, sl: str) -> str:
    """إنشاء صيغة webhook"""
    if script_type == 'INDICATOR':
        if alert_type == 'BUY':
            return (
                '{\n'
                f'  "symbol": "{symbol}",\n'
                f'  "qty": "{quantity}",\n'
                '  "action": "buy",\n'
                '  "market_position": "long",\n'
                f'  "tp": "{tp}",\n'
                f'  "sl": "{sl}",\n'
                '  "price": "{{close}}"\n'
                '}'
            )
        elif alert_type == 'SELL':
            return (
                '{\n'
                f'  "symbol": "{symbol}",\n'
                f'  "qty": "{quantity}",\n'
                '  "action": "sell",\n'
                '  "market_position": "short",\n'
                f'  "tp": "{tp}",\n'
                f'  "sl": "{sl}",\n'
                '  "price": "{{close}}"\n'
                '}'
            )
    elif script_type == 'STRATEGY':
        return (
            '{\n'
            f'  "symbol": "{symbol}",\n'
            f'  "qty": "{quantity}",\n'
            '  "action": "{{strategy.order.action}}",\n'
            '  "market_position": "{{strategy.market_position}}",\n'
            f'  "tp": "{tp}",\n'
            f'  "sl": "{sl}",\n'
            '  "price": "{{close}}"\n'
            '}'
        )
    return ''

if __name__ == "__main__":
    # التأكد من وجود الملفات المطلوبة
    required_files = ['auth.txt', 'ip_address.txt', 'signals.json']
    for file in required_files:
        if not os.path.exists(file):
            with open(file, 'w') as f:
                if file == 'signals.json':
                    f.write('[]')
                else:
                    f.write('')
    
    # تشغيل التطبيق
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)