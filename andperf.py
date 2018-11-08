import math
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from datetime import datetime
from functools import partial
from operator import attrgetter, itemgetter
from pprint import pprint
from subprocess import check_output
from typing import List, NamedTuple, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _sh(cmd: str) -> str:
    try:
        return check_output(cmd, shell=True).decode('utf-8')
    except Exception:
        raise SystemError(f"shell run cmd failed: {cmd}")


def _open(path: str):
    import webbrowser
    browser = webbrowser.get('chrome') or webbrowser.get(
        'firefox') or webbrowser.get('safari')
    if browser:
        browser.open(path)
    else:
        print('>>> ', path)


class Meminfo:
    """
     App Summary
                       Pss(KB)
                        ------
           Java Heap:    59680
         Native Heap:   149108
                Code:    53184
               Stack:       92
            Graphics:   106300
       Private Other:    15928
              System:     8701

               TOTAL:   392993       TOTAL SWAP PSS:      128
    """

    @staticmethod
    def dump(app: str):
        return Meminfo(_sh(f'adb shell dumpsys meminfo {app}'))

    def pie(self):
        data = vars(self)
        del data['TOTAL']
        pprint(data)
        plt.title(f"App Meminfo Pie")
        mems = list(data.values())
        total = sum(mems)
        plt.pie(mems,
                labels=list(data.keys()),
                wedgeprops=dict(width=0.5),
                startangle=-40,
                pctdistance=0.8,
                autopct=lambda pct: f'{pct * total / 100:.2f}M')
        plt.show()

    def _get_field(self, record: str, key: str) -> int:
        return int(re.search(rf'{key}:\s+(\d+)', record).group(1))

    def __init__(self, record: str):
        for field in (
                "Java Heap", "Native Heap", "Code", "Stack",
                "Graphics", "Private Other", "System", "TOTAL"):
            setattr(self, field.split()[0], int(
                self._get_field(record, field)) / 1024.0)


class AndPerf:

    def __init__(self):
        self._config = ConfigParser()
        self._config_file = os.path.expanduser('~/.AndPerf')
        try:
            self._config.read(self._config_file)
        except Exception:
            pass

    def _get_app(self, app: str) -> str:
        return self._config['android'].get('app', app)

    ################################
    # Config
    ################################

    def config(self, **kargs):
        """
        添加默认配置

        Parameters:
            - app: 默认的perf app，不用每次指定app参数
        """
        if 'android' not in self._config:
            self._config['android'] = {}

        for k, v in kargs.items():
            self._config['android'][k] = v
        with open(self._config_file, mode='w') as f:
            self._config.write(f)

        print('update config success')

    def get_config(self, key: str):
        print(self._config['android'].get(key, "not found"))

    def dump_config(self):
        """
        dump 当前的配置
        """
        for k, v in self._config['android'].items():
            print(f'{k} = {v}')

    ################################
    # Meminfo
    ################################

    def meminfo(self, *, app: str = None):
        """
        查看app当前的meminfo 信息
        """
        print(_sh(f"adb shell dumpsys meminfo {self._get_app(app)}"))

    def meminfo_pie(self, *, app: str = None):
        """
        将app的当前内存占用以饼图的形式展示出来
        """
        app = self._get_app(app)
        Meminfo.dump(app).pie()

    def meminfo_trend(self, period: int=1, app: str = None):
        """
        App 内存占用趋势图

        Parameters:
            - period: 每次采样的间隔，采样周期
            - app: app package name
        """
        def _dump():
            time.sleep(period)
            return Meminfo.dump(self._get_app(app))

        app = self._get_app(app)
        meminfos = []
        index = 0
        while True:
            try:
                index += 1
                print(f'dumping {app} meminfo.... {index}')
                meminfos.append(vars(Meminfo.dump(app)))
                time.sleep(period)
            except KeyboardInterrupt:
                break

        pd.DataFrame(meminfos).plot(grid=True)
        plt.title("App Meminfo Trend")
        plt.xlabel("Time")
        plt.ylabel("Mem / MB")
        plt.show()

    ################################
    # Helper
    ################################

    def dump_layout(self):
        """
        导出当前TOP Activity的布局
        """
        _sh('adb shell uiautomator dump /sdcard/window_dump.xml; adb pull /sdcard/window_dump.xml')
        path = f'file://{os.path.abspath(".")}/window_dump.xml'
        _open(path)

    def top_activity(self):
        """
        找出当前栈顶的页面
        """
        print()
        return _sh("adb shell dumpsys activity activities | grep ResumedActivity | tail -1 | awk '{print $4}'")

    def top_app(self):
        """
        当前活跃的app package name
        """
        print(self.top_activity().split('/')[0])

    def screencap(self, file: str="AndPerfScreencap.png"):
        """
        截图
        Parameters:
            - file: 截图保存的file
        """
        _sh(f"adb shell screencap /sdcard/screencap.png; adb pull /sdcard/screencap.png {file}")
        _open(f'file://{os.path.abspath(".")}/{file}')

    def dev_screen(self):
        """
        获取手机屏幕信息
        """
        print(_sh("adb shell wm size"))
        print("density:", _sh("adb shell getprop ro.sf.lcd_density"))

    def dev_mem(self):
        """
        设备内存大小信息
        """
        print(_sh("adb shell cat /proc/meminfo"))
        print("LOW MEM?", _sh("adb shell getprop ro.config.low_ram").strip() or "false")

    def systrace(self, *, app: str=None):
        """
        使用systrace
        """
        app = self._get_app(app)
        systrace = self._config['android'].get(
            'systrace', '~/Library/Android/sdk/platform-tools/systrace/systrace.py')

        if not os.path.exists(systrace):
            print("no found systrace.py, please config using key: systrace")
            return

        out = f'{app}_systrace.html'
        _sh(f"python2.7 {systrace} --app={app} --time=10 -o {out}")
        
        import webbrowser
        chrome = webbrowser.get('chrome')
        if chrome:
            chrome.open(f'file://{os.path.abspath(".")}/{out}')
        else:
            print(f'>>> 请使用chrome 打开 file://{os.path.abspath(".")}/{out}')

    ################################
    # Cpu Info
    ################################

    def cpuinfo(self):
        """
        查看当前的cpu信息
        """
        print(_sh("adb shell dumpsys cpuinfo"))

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

    def gfx_reset(self, *, app: str=None):
        app = self._get_app(app)
        _sh(f"adb shell dumpsys gfxinfo {app} reset")
        print('reset done!')

    def gfxinfo(self, *, app: str = None):
        """
        查看app的gfxinfo
        """
        print(_sh(f"adb shell dumpsys gfxinfo {self._get_app(app)}"))

    def gfx_hist(self, *, app: str = None):
        """
        查看每帧绘制耗时的 histogram 分布
        """
        gfx = _sh(f"adb shell dumpsys gfxinfo {self._get_app(app)}")
        GfxHistorgram(gfx).historgram()
        
    def fps(self, *, interval: int=2, plot: bool=True, app: str=None):
        fps_list = []
        while True:
            try:
                _sh(f'adb shell dumpsys gfxinfo {self._get_app(app)} reset 2>/dev/null')
                time.sleep(interval)
                gfx = _sh(f"adb shell dumpsys gfxinfo {self._get_app(app)}")
                fps = GfxHistorgram(gfx).fps()
                print('fps', fps)
                fps_list.append(fps)
            except KeyboardInterrupt:
                break

        if not plot:
            return
        series = pd.Series(fps_list, index=np.arange(len(fps_list)))
        plt.title("APP FPS")
        plt.xlabel("Time")
        plt.ylabel("Fps")
        series.plot.line(grid=True)
        plt.show()
        

class GfxFps:
    pass

class _Frame(NamedTuple):
    cost: int
    count: int

class GfxHistorgram:
    def __init__(self, gfxinfo:str):
        """
        HISTOGRAM: 5ms=0 6ms=0 7ms=0 8ms=0 9ms=0 10ms=0 
        """
        items = re.search(r'HISTOGRAM:\s*(.*)\s*', gfxinfo).group(1)
        def frame(item: str) -> _Frame:
            cost, count = item.strip().split('=')
            return _Frame(int(cost[:-2]), int(count))

        self.hists = [frame(item) for item in items.split() if frame(item)[1] > 0]
    
    def fps(self):
        if not self.hists:
            return 60

        renderd_frames = sum(count for _, count in self.hists)
        no_jank_frame_cost = 17.0

        def jank(cost, count) -> int:
            if cost <= no_jank_frame_cost:
                return 0
            else:
                return count * int(math.ceil(cost / no_jank_frame_cost)) - 1

        jank_frames = sum(jank(cost, count) for cost, count in self.hists)
        return int(60 * renderd_frames / (renderd_frames + jank_frames))

    def historgram(self):
        series = pd.Series(
                        data=list(map(itemgetter(1), self.hists)),
                        index=list(map(itemgetter(0), self.hists)))
        print(series)
        plt.title("gfx historgram")
        plt.xlabel('cost/ms')
        series.plot.bar(width=1)
        plt.show()

###########################
#
###########################

class TaskInfo(NamedTuple):
    name: str
    tid: str
    utime: int
    stime: int


class ProcessInfo(NamedTuple):
    name: str
    pid: str
    utime: int
    stime: int
    tasks: List[TaskInfo]


class TaskDiff(NamedTuple):
    name: str
    tid: str
    d_utime: int
    utime_percent: float
    d_stime: int
    stime_percent: float
    d_total_time: int
    t_percent: float


class StatThread:
    """
    线程统计
    """

    def __init__(self, app: str):
        self.proc_name = app

    def dump_process(self) -> ProcessInfo:
        start = time.time()
        pid = _sh(
            f"adb shell ps -ef 2>/dev/null | grep {self.proc_name} | head -1 | awk '{{print $2}}'").strip()
        if not pid:
            raise SystemExit(f'process: {self.proc_name} is not runing')

        tids = _sh(f'adb shell ls /proc/{pid}/task 2>/dev/null').split()

        with ThreadPoolExecutor(20) as pool:
            dump_t = partial(self.dump_thread, pid)
            tasks = [task for task in pool.map(dump_t, tids) if task]

        utime, stime = _sh(
            f'adb shell cat /proc/{pid}/stat 2>/dev/null').strip().split()[13:15]
        cost = time.time() - start
        print(f'dump process cost {cost:.2f}ms')
        return ProcessInfo(self.proc_name, pid, int(utime), int(stime), tasks)

    def dump_thread(self, pid: int, tid: int) -> TaskInfo:
        try:
            infos = _sh(
                f'adb shell cat /proc/{pid}/task/{tid}/stat').strip().split()
            name = infos[1]
            utime = int(infos[13])
            stime = int(infos[14])
            return TaskInfo(name, tid, utime, stime)
        except Exception as e:
            print(e)

    def _find_by_tid(self, task_infos: List[TaskInfo], tid: str) -> Optional[TaskInfo]:
        for task in task_infos:
            if task.tid == tid:
                return task

    def _diff(self, before_proc: ProcessInfo, after_proc: ProcessInfo):
        t_utime = after_proc.utime - before_proc.utime
        t_stime = after_proc.stime - before_proc.stime
        total_time = t_utime + t_stime

        print(); print('-' * 80)
        print('proc:', after_proc.name)
        print('thread count:', len(after_proc.tasks))
        print('proc_utime:', t_utime)
        print('proc_stime:', t_stime)
        print('-' * 80); print()

        before_proc.tasks.sort(key=attrgetter('tid'))
        after_proc.tasks.sort(key=attrgetter('tid'))

        stat_result = []

        task_t_utime = 0
        task_t_stime = 0
        task_t_time = 0

        for task in after_proc.tasks:
            b_task = self._find_by_tid(before_proc.tasks, task.tid) or TaskInfo(
                task.name, task.tid, 0, 0)
            d_utime = task.utime - b_task.utime
            d_stime = task.stime - b_task.stime
            d_time = d_utime + d_stime

            task_t_utime += d_utime
            task_t_stime += d_stime
            task_t_time += d_time

            diff = TaskDiff(
                task.name, task.tid,
                d_utime, d_utime / t_utime,
                d_stime, d_stime / t_stime,
                d_time, d_time / total_time)

            stat_result.append(diff)

        self._print_diff_result(stat_result)

    def _print_diff_result(self, stat_result):
        stat_result.sort(key=attrgetter('t_percent'), reverse=True)

        print('\033[7m%-20s %-6s | %-5s %-6s | %-5s %-6s | %6s %-s\033[0m' % (
            "NAME", "TID", "UTIME", "", "STIME", "", "U+S TIME", ""))

        def print_diff(diff: TaskDiff):
            print("%-20s %-6s | %-5s %-6s | %-5s %-6s | %6s %-s" % (
                diff.name, diff.tid,
                diff.d_utime, f'{diff.utime_percent * 100:.2f}%',
                diff.d_stime, f'{diff.stime_percent * 100:.2f}%',
                f'{abs(diff.t_percent) * 100:.2f}%', '=' * int(diff.t_percent * 100)))

        for diff in stat_result:
            if diff.t_percent < 0.01:
                break
            print_diff(diff)

    def stat_t(self, interval: int = 10):
        before_process_info = self.dump_process()

        if interval <= 0:
            pid = before_process_info.pid
            empty = ProcessInfo(self.proc_name, pid, 0, 0, [])
            self._diff(empty, before_process_info)
            return

        time.sleep(interval)
        after_process_info = self.dump_process()
        self._diff(before_process_info, after_process_info)


if __name__ == '__main__':
    import fire
    fire.Fire(AndPerf)
