import os
from configparser import ConfigParser


class AndPerfConfig:

    def __init__(self):
        self._config = ConfigParser()
        self._config_file = os.path.expanduser('~/.AndPerf')
        try:
            self._config.read(self._config_file)
        except Exception:
            pass

    def update(self, **kargs):
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

    def get(self, key: str, default : str = 'not found'):
        return self._config['android'].get(key, default)

    def dump(self):
        """
        dump 当前的配置
        """
        for k, v in self._config['android'].items():
            print(f'{k} = {v}')
