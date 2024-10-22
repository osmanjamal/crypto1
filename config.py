# المكتبات الخارجية
from flask import (
    Flask,
    request, 
    render_template, 
    redirect, 
    url_for, 
    flash
)

class Config:
    """إعدادات التطبيق"""
    
    # بيانات API بينانس
    BINANCE_API_KEY = ''    # أضف مفتاح API هنا
    BINANCE_API_SECRET = '' # أضف سر API هنا
    
    # إعدادات التداول
    LEVERAGE = 10
    DEFAULT_QUANTITY = 0.01
    USE_TRAILING_STOP = True
    TRAILING_STOP_PERCENT = 1.0
    
    # إعدادات الأمان
    SECRET_KEY = '123fdsgcsfgxgfg1514cgcd45'
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'
    Private_Key = '123456789'
    # إعدادات التيليجرام
    TELEGRAM_TOKEN = ''
    TELEGRAM_CHAT_ID = ''
    
    # قائمة العملات المدعومة
    SUPPORTED_PAIRS = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSD',
        'XRPUSDT', 'DOTUSDT', 'UNIUSDT', 'LINKUSDT', 'SOLUSD'
    ]
    
    @staticmethod
    def init_app(app):
        """تهيئة إعدادات التطبيق"""
        app.config['SECRET_KEY'] = Config.SECRET_KEY