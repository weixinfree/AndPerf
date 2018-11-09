import math
import re
import time
from operator import itemgetter
from typing import NamedTuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from andperf._util import sh


class _Frame(NamedTuple):
    cost: int
    count: int


class Gfxinfo:

    @staticmethod
    def reset(app: str):
        sh(f"adb shell dumpsys gfxinfo {app} reset 2>/dev/null")

    @staticmethod
    def dump(app: str):
        gfxinfo = sh(f"adb shell dumpsys gfxinfo {app}")
        return Gfxinfo(gfxinfo)

    @staticmethod
    def trend(app: str, interval: int, plot: bool):
        print('using Ctrl+C to show a trend figure')
        print()
        
        fps_list = []
        while True:
            try:
                Gfxinfo.reset(app)
                time.sleep(interval)
                fps = Gfxinfo.dump(app).compute_fps()
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

    def __init__(self, gfxinfo: str):
        """
        HISTOGRAM: 5ms=0 6ms=0 7ms=0 8ms=0 9ms=0 10ms=0 
        """
        self.gfxinfo = gfxinfo

        items = re.search(r'HISTOGRAM:\s*(.*)\s*', gfxinfo).group(1)

        def frame(item: str) -> _Frame:
            cost, count = item.strip().split('=')
            return _Frame(int(cost[:-2]), int(count))

        self.hists = [frame(item)
                      for item in items.split() if frame(item)[1] > 0]

    def compute_fps(self):
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

    def hist(self):
        series = pd.Series(
            data=list(map(itemgetter(1), self.hists)),
            index=list(map(itemgetter(0), self.hists)))
        print(series)
        plt.title("gfx historgram")
        plt.xlabel('cost/ms')
        series.plot.bar(width=1)
        plt.show()
