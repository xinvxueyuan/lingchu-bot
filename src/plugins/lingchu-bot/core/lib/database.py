from nonebot import get_driver
import sqlite3
from pathlib import Path
from queue import Queue
from typing import Dict, List, Tuple, Any, Union
from contextlib import contextmanager
from typing import Iterator, Callable, TypeVar, Coroutine

# 数据库连接池配置
_db_pool: Queue[sqlite3.Connection] = Queue(maxsize=5)  # 数据库连接池
_all_connections: List[sqlite3.Connection] = []  # 所有活跃连接列表
DB_PATH = Path(__file__).parent.parent.parent / "data/groups/groups.db"  # 数据库文件路径

def _validate_identifier(name: str) -> None:
    """验证字符串是否为有效的SQL标识符
    
    参数:
        name: 需要验证的字符串
        
    异常:
        ValueError: 当名称不是有效标识符时抛出
    """
    if not name.isidentifier():
        raise ValueError(f"无效的标识符: {name}")

def _execute_check(conn: sqlite3.Connection, query: str, params: tuple = ()) -> bool:
    """执行SQL查询并检查是否有结果
    
    参数:
        conn: 数据库连接对象
        query: 要执行的SQL语句
        params: 查询参数元组
        
    返回:
        bool: 查询是否有结果
    """
    return bool(conn.execute(query, params).fetchone())

def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """检查表是否存在于数据库中
    
    参数:
        conn: 数据库连接对象
        table_name: 要检查的表名
        
    返回:
        bool: 表是否存在
    """
    return _execute_check(
        conn,
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )

def init_db_pool() -> None:
    """初始化数据库连接池
    
    创建5个数据库连接并放入连接池，同时初始化必要的数据库表结构
    """
    if not _db_pool.empty(): 
        return
        
    # 确保数据库目录和文件存在
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        DB_PATH.touch()
    
    # 初始化连接池
    for _ in range(5):
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL") 
        _db_pool.put(conn)
        _all_connections.append(conn)
    

@get_driver().on_shutdown
async def close_db_connections() -> None:
    """关闭所有数据库连接
    
    在应用关闭时调用，确保所有连接被正确关闭
    """
    for conn in _all_connections:
        conn.close()
    _all_connections.clear()

T = TypeVar('T')

@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """获取数据库连接的上下文管理器
    
    使用连接池管理连接，自动处理事务提交和回滚
    
    返回:
        Iterator[sqlite3.Connection]: 可用的数据库连接
        
    注意:
        在with块结束时自动提交事务，发生异常时回滚
    """
    conn = _db_pool.get()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _db_pool.put(conn)

def _with_connection(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    """数据库操作装饰器
    
    自动为异步数据库操作提供连接管理
    
    参数:
        func: 需要包装的异步函数
        
    返回:
        Callable: 包装后的函数
    """
    async def wrapper(operation_type: str, table_name: str, **kwargs) -> T:
        with get_connection() as conn:
            return await func(conn, operation_type=operation_type, table_name=table_name, **kwargs)
    return wrapper

@_with_connection
async def db_operation(
    conn: sqlite3.Connection,
    operation_type: str,
    table_name: str,
    **kwargs: Any
) -> Union[bool, List[Tuple[Any, ...]]]:
    """统一数据库操作接口
    
    支持多种数据库操作类型，包括表管理和数据CRUD
    
    参数:
        conn: 数据库连接对象
        operation_type: 操作类型，支持:
            - 'create_table': 创建表
            - 'delete_table': 删除表
            - 'alter_column': 修改列
            - 'insert': 插入数据
            - 'update': 更新数据
            - 'delete': 删除数据
            - 'query': 查询数据
            - 'batch_insert': 批量插入
            - 'clean_expired_tasks': 清理过期任务
        table_name: 操作的目标表名
        **kwargs: 操作所需的其他参数
        
    返回:
        根据操作类型返回:
        - bool: 操作是否成功
        - List[Tuple]: 查询结果集
        
    异常:
        ValueError: 当表不存在或操作类型无效时抛出
    """
    _validate_identifier(table_name)
    if not _table_exists(conn, table_name) and operation_type != "create_table":
        raise ValueError(f"表不存在: {table_name}")

    # 表结构操作
    if operation_type == "create_table":
        if _table_exists(conn, table_name): 
            return False
        columns = kwargs.get("columns", ["id INTEGER PRIMARY KEY AUTOINCREMENT"])
        conn.execute(f"CREATE TABLE \"{table_name}\" ({', '.join(columns)})")
        return True

    elif operation_type == "delete_table":
        conn.execute(f"DROP TABLE \"{table_name}\"")
        return True

    elif operation_type == "alter_column":
        column_name = kwargs["column_name"]
        _validate_identifier(column_name)
        exists = any(col[1] == column_name for col in 
                    conn.execute(f"PRAGMA table_info({table_name})"))
        
        if kwargs["action"] == "add" and not exists:
            conn.execute(f"ALTER TABLE \"{table_name}\" ADD COLUMN \"{column_name}\" {kwargs.get('column_type', 'TEXT')}")
            return True
        elif kwargs["action"] == "drop" and exists:
            conn.execute(f"ALTER TABLE \"{table_name}\" DROP COLUMN \"{column_name}\"")
            return True
        return False

    # 数据操作
    elif operation_type in ("insert", "update", "delete", "query", "batch_insert"):
        if operation_type == "insert":
            data = kwargs["data"]
            columns = ", ".join(f'"{k}"' for k in data)
            conn.execute(
                f"INSERT INTO \"{table_name}\" ({columns}) VALUES ({', '.join('?'*len(data))})",
                tuple(data.values())
            )
            return True
            
        elif operation_type == "update":
            conn.execute(
                f"UPDATE \"{table_name}\" SET {', '.join(f'\"{k}\"=?' for k in kwargs['data'])} WHERE {kwargs['condition']}",
                tuple(kwargs["data"].values()) + tuple(kwargs.get("params", ()))
            )
            return True
            
        elif operation_type == "delete":
            conn.execute(f"DELETE FROM \"{table_name}\" WHERE {kwargs['condition']}", kwargs.get("params", ()))
            return True
            
        elif operation_type == "query":
            query = f"SELECT {kwargs.get('columns', '*')} FROM \"{table_name}\""
            if kwargs.get("condition"):
                query += f" WHERE {kwargs['condition']}"
            if kwargs.get("limit"):
                query += f" LIMIT {kwargs['limit']}"
            return conn.execute(query, kwargs.get("params", ())).fetchall()
            
        elif operation_type == "batch_insert":
            data_list: List[Dict[str, Any]] = kwargs["data_list"]
            if not data_list:
                return False
                
            columns = ", ".join(f'"{k}"' for k in data_list[0])
            placeholders = ", ".join('?' * len(data_list[0]))
            values = [tuple(item.values()) for item in data_list]
            
            conn.executemany(
                f"INSERT INTO \"{table_name}\" ({columns}) VALUES ({placeholders})",
                values
            )
            return True


        
    raise ValueError(f"无效的操作类型: {operation_type}")