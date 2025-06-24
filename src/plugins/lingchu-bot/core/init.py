from .lib.state import check_plugins_state
from .lib.database import init_db_pool

# 初始化数据库连接池
init_db_pool()

if check_plugins_state():
    from .admin.index import *
    from .lib.index import *
