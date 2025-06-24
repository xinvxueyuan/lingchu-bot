from .lib.state import check_plugins_state


if check_plugins_state():
    from .admin.index import *
    from .lib.index import *
