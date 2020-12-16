import os
import json
from pathlib import Path
from json import JSONDecodeError
from datetime import datetime, timedelta


class ScheduleServices:

    def __init__(self):
        pass

    @staticmethod
    def strtodatetime(datetime_str):
        if isinstance(datetime_str, datetime):
            datetime_str = datetime_str.strftime("%Y-%m-%d %H:%M:%S")

        return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def diff_dates(now, later):
        diff = later - now
        hours = divmod(diff.total_seconds(), 3600)[0]
        minutes = divmod(diff.total_seconds(), 60)[0] - (hours * 60)
        seconds = diff.total_seconds() - (hours * 3600) - (minutes * 60)
        return f'{hours:.0f}h', f' {round(minutes):.0f}m', f' {seconds:.0f}s'

    @staticmethod
    def explode_minutes(minutes):
        hours = int(minutes / 60)
        minutes = minutes - (hours * 60)

        return f'{hours}h {minutes}m'

    # @staticmethod
    # async def get_delay_delta():
    #     try:
    #         directory = os.path.dirname(__file__)
    #         file = os.path.join(directory, 'delay.json')
    #         session_data_file = Path(file)
    #         with open(session_data_file, 'r') as f:
    #             data = json.load(f)
    #             f.close()
    #             hours = divmod(data[0], 60)[0]
    #             minutes = data[0] - (hours * 60)
    #             delay_delta = timedelta(hours=hours, minutes=minutes)
    #             return delay_delta
    #     except JSONDecodeError as e:
    #         print(f'{JSONDecodeError}: {e}')
    #         return None

    async def get_refresh_datetime(self):
        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/schedule_refresh.json')
            session_data_file = Path(file)
            with open(session_data_file, 'r') as f:
                data = json.load(f)
                if len(data) == 0:
                    return datetime.utcnow()
                f.close()
                return self.strtodatetime(data[0])
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return None

    @staticmethod
    def save_refresh_datetime(new_dt):
        def datetime_format(o):
            if isinstance(o, datetime):
                return o.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return o

        try:
            directory = os.path.dirname(__file__)
            file = os.path.join(directory, 'data/schedule_refresh.json')
            data_file = Path(file)
            with open(data_file, 'w') as f:
                f.write(json.dumps([new_dt], indent=4, default=datetime_format))
                f.close()
                return True
        except JSONDecodeError as e:
            print(f'{JSONDecodeError}: {e}')
            return False
