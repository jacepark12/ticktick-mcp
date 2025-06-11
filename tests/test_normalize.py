import importlib
import os
from ticktick_mcp.src import server


def reload_server_with_tz(tz: str):
    os.environ['TICKTICK_USER_TIMEZONE'] = tz
    importlib.reload(server)


def test_normalize_datetime_for_user():
    reload_server_with_tz('Asia/Bangkok')  # UTC+7
    result = server.normalize_datetime_for_user('2025-06-11T15:00:00')
    assert result == '2025-06-11T15:00:00+0700'

