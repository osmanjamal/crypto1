class Config:
    # بيانات API بينانس
    BINANCE_API_KEY = 'BINANCE_API_KEY'
    BINANCE_API_SECRET = 'BINANCE_API_SECRET'
    
    # إعدادات التداول
    LEVERAGE = 10
    DEFAULT_TIMEFRAME = '1h'
    MAX_POSITIONS = 5
    DEFAULT_QUANTITY = 0.01
    USE_TRAILING_STOP = True
    TRAILING_STOP_PERCENT = 1.0
    
    # إعدادات الأمان
    SECRET_KEY = '123fdsgcsfgxgfg1514cgcd45'
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'
    
    # إعدادات التيليجرام
    TELEGRAM_TOKEN = ''
    TELEGRAM_CHAT_ID = ''
    
    # قائمة العملات المدعومة
    SUPPORTED_PAIRS = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT',
        'XRPUSDT', 'DOTUSDT', 'UNIUSDT', 'LINKUSDT', 'SOLUSDT'
    ]
