import os
import re
import sys

__all__ = ('MPD_HOST', 'MPD_PORT', 'MPD_PASSWORD')

pattern = re.compile(
    r'(?:(?P<password>.*)@)?(?P<host>[a-zA-Z0-9.-]+)(?::(?P<port>\d+))?'
)

try:
    matched = pattern.match(os.getenv('MPD_HOST'))
    MPD_HOST = matched.group('host')
    MPD_PORT = int(matched.group('port') or 6600)
    MPD_PASSWORD = matched.group('password')
except Exception as e:
    print(e, file=sys.stderr)
    MPD_HOST = 'localhost'
    MPD_PORT = 6600
    MPD_PASSWORD = None
