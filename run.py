from companion.supervisor import entry
if __name__ == '__main__':
    try:entry()
    except Exception as error:
        import logging,sys
        logging.exception('Eddy Deck no pudo iniciar o terminó inesperadamente.')
        if getattr(sys,'frozen',False):
            import ctypes
            from companion.storage import startup_message
            ctypes.windll.user32.MessageBoxW(None,startup_message(error),'Eddy Deck · Problema al iniciar',0x10)
        sys.exit(1)
