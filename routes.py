from main import app
from flask import render_template, request, redirect, url_for, flash
import config
import importlib
from functions import *
import pandas as pd

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''

    if request.method == 'POST':
        if request.form.get('username') != config.admin_username or \
                request.form.get('password') != config.admin_password:
            error = 'Invalid Credentials. Please try again.'
            flash(format('Invalid credentials. Please try again.'), 'error')
        else:
            #auth_data = request.form.to_dict(flat=True)
            write('auth.txt', 'authenticated')
            write('ip_address.txt', ip_address())
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    write('auth.txt', 'unauthenticated')
    write('ip_address.txt', '')
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def main():
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()
    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('index'))

@app.route('/password_reset',methods=['POST'])
def reset_password():
    if request.method == 'POST':
        admin_username = request.form.get('current_username')
        old_pass = request.form.get('current_password')
        new_pass = request.form.get('new_password')
        if admin_username == config.admin_username:
            if old_pass == config.admin_password:
                config.admin_password = new_pass
                with open('config.py', 'r') as f:
                    config_contents = f.read()
                new_config_contents = config_contents.replace(
                    f"admin_password = '{old_pass}'", f"admin_password = '{new_pass}'")
                with open('config.py', 'w') as f:
                    f.write(new_config_contents)
                    flash(format('Admin Password Changed Successfuly'), 'success')

            else:
                flash(format('Current Admin Password Is Not Valid'), 'error')
        else:
            flash(format('Admin Username Is Not Valid'), 'error')
    return redirect(url_for('change_password'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():        
    pass
    return render_template('change_password.html')



@app.route('/dashboard', methods=['GET', 'POST'])
async def index():
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()

    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        quantity = request.form.get('qty', "")
        symbol = request.form.get('symbol', "")
        alert_type = request.form.get('alert_type', "")
    
        if alert_type == 'BUY':
            syntax = '{</br>"symbol": ' + '"' + symbol + '",\
                        </br>"qty": ' + '"' + quantity + '",\
                        </br>"action": "buy",\
                        </br>"market_position": "long",\
                        </br>"price": "{{close}}"</br>''}'

        elif alert_type == 'SELL':
            syntax = '{</br>"symbol": ' + '"' + symbol + '",\
                        </br>"qty": ' + '"' + quantity + '",\
                        </br>"action": "sell",\
                        </br>"market_position": "short",\
                        </br>"price": "{{close}}"</br>''}'

        return render_template('index.html', syntax=syntax)
    else:
        return render_template('index.html')


@app.route('/signals', methods=['GET', 'POST'])
async def signals():
  auth_session = read('auth.txt')
  ip_session = str(read('ip_address.txt'))
  ip_add = ip_address()
    
  if auth_session != 'authenticated' or ip_session != ip_add:
    return redirect(url_for('login'))
  with open('signals.json', 'r') as f:
    trade_data = json.load(f)
    df = pd.DataFrame(
      trade_data,
      columns=['order_time', 'symbol', 'action', 'entry', 'qty', 'qty_type'])
    df.rename(columns={
      'order_time': 'TIME',
      'symbol': 'SYMBOL',
      'action': 'SIDE',
      'qty': 'QTY',
      'entry': 'ENTRY',
      # 'tp': 'TP',
      # 'sl': 'SL',
      'qty_type': 'ACCOUNT'
    },
              inplace=True)
    df = df.sort_values(by="TIME", ascending=False)
    #print(df)

  return render_template('signals.html',
                         tables=[df.to_html(classes='data')],
                         titles=df.columns.values)


@app.route('/trades', methods=['GET', 'POST'])
async def trades():
  auth_session = read('auth.txt')
  ip_session = str(read('ip_address.txt'))
  ip_add = ip_address()

  if auth_session != 'authenticated' or ip_session != ip_add:
    return redirect(url_for('login'))
  with open('trades.json', 'r') as f:
    trade_data = json.load(f)
    df = pd.DataFrame(
      trade_data,
      columns=['order_time', 'order_id', 'symbol', 'action', 'price', 'qty'])
    df.rename(columns={
      'order_time': 'TIME',
      'order_id': 'ORDER ID',
      'symbol': 'SYMBOL',
      'action': 'SIDE',
      'qty': 'QTY',
      'price': 'PRICE'
    },
              inplace=True)
    df = df.sort_values(by="TIME", ascending=False)
    #print(df)

  return render_template('trades.html',
                         tables=[df.to_html(classes='data')],
                         titles=df.columns.values)

@app.route('/max_loss_settings', methods=['GET', 'POST'])
def max_loss_settings():
  auth_session = read('auth.txt')
  ip_session = str(read('ip_address.txt'))
  ip_add = ip_address()

  if auth_session != 'authenticated' or ip_session != ip_add:
    return redirect(url_for('login'))
  max_loss_value = read('max_loss_value.txt')
  if len(max_loss_value) > 0:
    max_loss_value = max_loss_value
  else:
    max_loss_value = 0

  if request.method == 'POST':
    max_loss_value = request.form.get('max_loss', "")
    if len(max_loss_value) > 0:
      write('max_loss_value.txt',max_loss_value)
    if max_loss_value == '':
      max_loss_value = 0
    return render_template('settings.html',max_loss_value=max_loss_value)

  return render_template('settings.html',max_loss_value=max_loss_value)

@app.route('/reset_max_loss', methods=['GET', 'POST'])
def reset_max_loss():
  auth_session = read('auth.txt')
  ip_session = str(read('ip_address.txt'))
  ip_add = ip_address()

  if auth_session != 'authenticated' or ip_session != ip_add:
    return redirect(url_for('login'))
  if request.method == 'POST':
    write('max_loss.txt','')

    return redirect(url_for('max_loss_settings'))

def get_display_data(value, default='NO'):
    if len(value) > 0:
        return value[:len(value) - 5] + '************'
    else:
        return default

@app.route('/api_settings', methods=['GET', 'POST'])
def api_settings():
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()

    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    importlib.reload(config)

    login = config.login
    half_lenght = int((len(str(config.password))/2)*1.25)
    password = config.password[:len(str(config.password))-half_lenght] + '************'
    server = config.server

    return render_template('add_api.html',login=login,password=password,server=server)


def process_value(value, account_number):
    if len(str(value)) > 0:
        return value[:len(str(value))-5] + '************'
    else:
        return f'NO_VALUE_FOUND_{account_number}'



@app.route('/add_metaapi_<int:account_number>', methods=['GET', 'POST'])
def add_metaapi(account_number):
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()

    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    importlib.reload(config)
    
    token_key = f'token_{account_number}'
    account_id_key = f'account_id_{account_number}'
    
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        server = request.form.get('server')
        
        if len(login) > 0 and len(password) > 0 and len(server) > 0:
            update_config('login = ', login, 'password = ', password, 'server = ', server)
            # importlib.reload(login)
    return redirect(url_for('api_settings'))

@app.route('/add_api_telegram_<int:account_number>', methods=['GET', 'POST'])
def add_api_telegram(account_number):
    auth_session = read('auth.txt')
    ip_session = str(read('ip_address.txt'))
    ip_add = ip_address()

    if auth_session != 'authenticated' or ip_session != ip_add:
        return redirect(url_for('login'))
    importlib.reload(config)
    
    tg_token_key = f'tg_token_{account_number}'
    tg_channel_key = f'tg_channel_{account_number}'
    
    if request.method == 'POST':
        tg_token = request.form.get('tg_token')
        tg_channel = request.form.get('tg_channel')
        
        if len(tg_token) > 0 and len(tg_channel) > 0:
            update_config(f'{tg_token_key} = ', tg_token, f'{tg_channel_key} = ', tg_channel)
            
    return redirect(url_for('api_settings'))