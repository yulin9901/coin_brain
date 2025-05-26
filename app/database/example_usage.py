#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
数据库管理器使用示例
这个文件展示了如何使用DatabaseManager类来简化数据库操作
"""

from app.database.db_manager import DatabaseManager
from app.utils import get_db_config, load_config

def example_query_with_context_manager():
    """使用上下文管理器方式查询数据示例"""
    config = load_config()
    db_config = get_db_config(config)
    db_manager = DatabaseManager(db_config)
    
    # 使用上下文管理器方式，自动处理连接的打开和关闭
    with db_manager.get_connection(dictionary=True) as (connection, cursor):
        # 创建表（如果不存在）
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS example_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            value INT
        )
        """)
        
        # 插入数据
        cursor.execute(
            "INSERT INTO example_table (name, value) VALUES (%s, %s)",
            ("测试数据", 100)
        )
        
        # 查询数据
        cursor.execute("SELECT * FROM example_table")
        results = cursor.fetchall()
        
        # 提交事务
        connection.commit()
        
        print("查询结果:", results)
    
    # 连接在with块结束时自动关闭

def example_simplified_methods():
    """使用简化方法示例"""
    config = load_config()
    db_config = get_db_config(config)
    db_manager = DatabaseManager(db_config)
    
    # 执行查询并获取结果
    results = db_manager.execute_query(
        "SELECT * FROM example_table WHERE value > %s",
        {"value": 50},
        dictionary=True
    )
    print("查询结果:", results)
    
    # 执行更新操作
    affected_rows = db_manager.execute_update(
        "UPDATE example_table SET value = %s WHERE name = %s",
        {"value": 200, "name": "测试数据"}
    )
    print(f"更新了 {affected_rows} 行数据")
    
    # 批量插入数据
    data_to_insert = [
        ("批量数据1", 101),
        ("批量数据2", 102),
        ("批量数据3", 103)
    ]
    inserted_rows = db_manager.execute_many(
        "INSERT INTO example_table (name, value) VALUES (%s, %s)",
        data_to_insert
    )
    print(f"插入了 {inserted_rows} 行数据")

if __name__ == "__main__":
    print("数据库管理器使用示例")
    example_query_with_context_manager()
    example_simplified_methods()
