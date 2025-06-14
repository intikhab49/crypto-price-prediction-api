    print("--- Attempting to import config from test_config_load.py ---")
    import sys
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path}") # Shows where Python looks for modules

    try:
        # Try to force Python to tell us where it *would* load 'config' from
        import importlib.util
        spec = importlib.util.find_spec("config")
        if spec and spec.origin:
            print(f"Found 'config' module at: {spec.origin}")
        else:
            print("'config' module not found by importlib.util.find_spec.")

        from config import settings, TIMEFRAME_MAP, FEATURE_LIST # Ensure FEATURE_LIST is also imported if config.py defines it
        print("--- config module imported successfully into test_config_load.py ---")
        
        print(f"settings object type: {type(settings)}")
        
        print(f"TIMEFRAME_MAP['30m']['period'] = {TIMEFRAME_MAP.get('30m', {}).get('period')}")
        print(f"TIMEFRAME_MAP['30m']['min_samples'] = {TIMEFRAME_MAP.get('30m', {}).get('min_samples')}")
        
        print(f"TIMEFRAME_MAP['4h']['period'] = {TIMEFRAME_MAP.get('4h', {}).get('period')}")
        print(f"TIMEFRAME_MAP['24h']['period'] = {TIMEFRAME_MAP.get('24h', {}).get('period')}")
        
        if hasattr(settings, 'MIN_PRICE_POINTS'):
            print(f"settings.MIN_PRICE_POINTS = {settings.MIN_PRICE_POINTS}")
        else:
            print("settings.MIN_PRICE_POINTS is NOT defined on the settings object.")
            # print("Attributes of settings object:", dir(settings)) # Potentially long, uncomment if needed

    except ImportError as e:
        print(f"ImportError in test_config_load.py: {e}")
        import traceback
        traceback.print_exc()
    except AttributeError as e:
        print(f"AttributeError in test_config_load.py: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"Some other exception in test_config_load.py: {e}")
        import traceback
        traceback.print_exc()

    print("--- End of test_config_load.py ---")