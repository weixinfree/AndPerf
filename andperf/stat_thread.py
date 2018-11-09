import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from operator import attrgetter, itemgetter
from typing import List, NamedTuple, Optional

from andperf._util import sh


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
        data = sh(f"adb shell ps -ef 2>/dev/null").strip()

        for line in data.splitlines():
            segs = line.strip().split()
            if segs[-1] == self.proc_name:
                pid = segs[1]

        if not pid:
            raise SystemExit(f'process: {self.proc_name} is not runing')

        tids = sh(f'adb shell ls /proc/{pid}/task 2>/dev/null').split()

        with ThreadPoolExecutor(20) as pool:
            dump_t = partial(self.dump_thread, pid)
            tasks = [task for task in pool.map(dump_t, tids) if task]

        utime, stime = sh(
            f'adb shell cat /proc/{pid}/stat 2>/dev/null').strip().split()[13:15]
        cost = time.time() - start
        print(f'dump process cost {cost:.2f}ms')
        return ProcessInfo(self.proc_name, pid, int(utime), int(stime), tasks)

    def dump_thread(self, pid: int, tid: int) -> TaskInfo:
        try:
            infos = sh(
                f'adb shell cat /proc/{pid}/task/{tid}/stat 2>/dev/null').strip().split()
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

        self._print_process(after_proc, t_utime, t_stime)

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

    def _print_process(self, after_proc, t_utime, t_stime):
        print()
        print('-' * 80)
        print('proc:', after_proc.name)
        print('thread count:', len(after_proc.tasks))
        print('proc_utime:', t_utime)
        print('proc_stime:', t_stime)
        print('-' * 80)
        print()

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
