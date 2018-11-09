from subprocess import check_output


def sh(cmd: str) -> str:
    try:
        return check_output(cmd, shell=True).decode('utf-8')
    except Exception:
        raise SystemError(f"shell run cmd failed: {cmd}")


def open_with_webbrowser(path: str):
    import webbrowser
    browser = webbrowser.get('chrome') or webbrowser.get(
        'firefox') or webbrowser.get('safari')
    if browser:
        browser.open(path)
    else:
        print('>>> ', path)
