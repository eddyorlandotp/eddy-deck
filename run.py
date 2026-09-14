from companion.supervisor import entry
if __name__ == '__main__':
    try:
        import sys
        if len(sys.argv)==3 and sys.argv[1]=='--focus-window':
            from companion.focus import main
            main()
        elif len(sys.argv)==3 and sys.argv[1]=='--launch-application':
            from companion.launch_worker import main
            main()
        else:entry()
    except Exception as error:
        import logging,sys
        logging.exception('Eddy Deck no pudo iniciar o terminó inesperadamente.')
        if getattr(sys,'frozen',False) and not any(flag in sys.argv for flag in ('--focus-window','--launch-application')):
            import ctypes
            from companion.storage import startup_message
            ctypes.windll.user32.MessageBoxW(None,startup_message(error),'Eddy Deck · Problema al iniciar',0x10)
        sys.exit(1)
