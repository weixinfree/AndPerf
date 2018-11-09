import os

from andperf._config import AndPerfConfig
from andperf._util import open_with_webbrowser, sh
from andperf.gfxinfo import Gfxinfo
from andperf.meminfo import Meminfo
from andperf.stat_thread import StatThread


class AndPerf:

    def __init__(self):
        self._config = AndPerfConfig()

    def _get_app(self, app: str) -> str:
        return self._config.get('app', app)

    ################################
    # Config
    ################################

    def config(self, **kargs):
        """
        添加默认配置

        Parameters:
            - app: 默认的perf app，不用每次指定app参数
        """
        self._config.update(**kargs)

    def dump_config(self):
        """
        dump 当前的配置
        """
        self._config.dump()

    ################################
    # Meminfo
    ################################

    def meminfo(self, *, app: str = None):
        """
        查看app当前的meminfo 信息
        """
        return Meminfo.dump(self._get_app(app)).meminfo

    def meminfo_pie(self, *, app: str = None):
        """
        将app的当前内存占用以饼图的形式展示出来
        """
        Meminfo.dump(self._get_app(app)).pie()

    def meminfo_trend(self, period: int = 1, app: str = None):
        """
        App 内存占用趋势图

        Parameters:
            - period: 每次采样的间隔，采样周期
            - app: app package name
        """
        Meminfo.trend(self._get_app(app), period)
    
    ################################
    # Cpu Info
    ################################

    def cpuinfo(self):
        """
        查看当前的cpu信息
        """
        print(sh("adb shell dumpsys cpuinfo"))

    def stat_thread(self, *, interval: int = 10, app: str = None):
        """
        统计一段时间内App内各个线程cpu时间片占比

        Paramters:
            - interval: 统计间隔
        """
        StatThread(self._get_app(app)).stat_t(interval)

    ################################
    # Gfx Info
    ################################

    def gfx_reset(self, *, app: str = None):
        app = self._get_app(app)
        Gfxinfo.reset(app)
        print('reset done!')

    def gfxinfo(self, *, app: str = None):
        """
        查看app的gfxinfo
        """
        return Gfxinfo.dump(self._get_app(app)).gfxinfo

    def gfx_hist(self, *, app: str = None):
        """
        查看每帧绘制耗时的直方图分布
        """
        Gfxinfo.dump(self._get_app(app)).hist()

    def gfx_fps(self, *, interval: int = 2, plot: bool = True, app: str = None):
        """
        计算fps, 并绘制fps变化走势图
        """
        Gfxinfo.trend(self._get_app(app), interval, plot)

    ################################
    # Helper
    ################################

    def dump_layout(self):
        """
        导出当前TOP Activity的布局
        """
        sh('adb shell uiautomator dump /sdcard/window_dump.xml; adb pull /sdcard/window_dump.xml')
        path = f'file://{os.path.abspath(".")}/window_dump.xml'
        open_with_webbrowser(path)

    def top_activity(self):
        """
        找出当前栈顶的页面
        """
        print()
        return sh("adb shell dumpsys activity activities | grep ResumedActivity | tail -1 | awk '{print $4}'")

    def top_app(self):
        """
        当前活跃的app package name
        """
        print(self.top_activity().split('/')[0])

    def screencap(self, file: str = "AndPerfScreencap.png"):
        """
        截图
        Parameters:
            - file: 截图保存的file
        """
        sh(f"adb shell screencap /sdcard/screencap.png; adb pull /sdcard/screencap.png {file}")
        open_with_webbrowser(f'file://{os.path.abspath(".")}/{file}')

    def dev_screen(self):
        """
        获取手机屏幕信息
        """
        print(sh("adb shell wm size"))
        print("density:", sh("adb shell getprop ro.sf.lcd_density"))

    def dev_mem(self):
        """
        设备内存大小信息
        """
        print(sh("adb shell cat /proc/meminfo"))
        print("LOW MEM?", sh("adb shell getprop ro.config.low_ram").strip() or "false")

    def systrace(self, *, app: str = None):
        """
        使用systrace
        """
        app = self._get_app(app)
        systrace = self._config.get(
            'systrace', '~/Library/Android/sdk/platform-tools/systrace/systrace.py')
        
        if not os.path.exists(os.path.expanduser(systrace)):
            print("no found systrace.py, please config using key: systrace")
            return

        print('wait for a while, generating systrace')

        out = f'{app}_systrace.html'
        try:
            sh(f"python2.7 {systrace} --app={app} --time=10 -o {out}")
        except Exception:
            print("need cmd python2.7 avaliable in path")
            return
        

        import webbrowser
        chrome = webbrowser.get('chrome')
        if chrome:
            chrome.open(f'file://{os.path.abspath(".")}/{out}')
        else:
            print(f'>>> 请使用chrome 打开 file://{os.path.abspath(".")}/{out}')


def main():
    import fire
    fire.Fire(AndPerf)


if __name__ == '__main__':
    main()
