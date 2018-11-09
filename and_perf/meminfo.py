import re
import time
from pprint import pprint

import matplotlib.pyplot as plt
import pandas as pd

from _util import sh


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
    def trend(app: str, period: int):

        print('using Ctrl+C to show a meminfo trend')
        print()

        def _dump():
            time.sleep(period)
            return Meminfo.dump(app)

        meminfos = []
        index = 0
        while True:
            try:
                index += 1
                meminfo = Meminfo.dump(app)
                print(f'dumping {app} meminfo.... {index}, TOTAL: {meminfo.TOTAL:.2f}MB')
                meminfos.append(vars(meminfo))
                time.sleep(period)
            except KeyboardInterrupt:
                break

        pd.DataFrame(meminfos).plot()
        plt.title("App Meminfo Trend")
        plt.xlabel("Time")
        plt.ylabel("Mem / MB")
        plt.show()

    @staticmethod
    def dump(app: str):
        return Meminfo(sh(f'adb shell dumpsys meminfo {app}'))

    def pie(self):
        data = vars(self)
        del data['TOTAL']
        del data['meminfo']

        pprint(data)
        plt.title(f"App Meminfo Pie")
        mems = list(data.values())
        total = sum(mems)
        plt.pie(mems,
                labels=list(data.keys()),
                wedgeprops=dict(width=0.5),
                startangle=90,
                pctdistance=0.8,
                autopct=lambda pct: f'{pct * total / 100:.2f}M')
        plt.show()

    @staticmethod
    def _get_field(record: str, key: str) -> int:
        return int(re.search(rf'{key}:\s+(\d+)', record).group(1))

    def __init__(self, meminfo: str):

        self.meminfo = meminfo

        for field in (
                "Java Heap", "Native Heap", "Code", "Stack",
                "Graphics", "Private Other", "System", "TOTAL"):

            setattr(
                self, 
                field.split()[0], 
                int( Meminfo._get_field(meminfo, field)) / 1024.0)
