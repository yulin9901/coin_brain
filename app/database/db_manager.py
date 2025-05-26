#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import mysql.connector
from contextlib import contextmanager

class DatabaseManager:
    """
    数据库连接管理器，提供统一的数据库连接管理。
    使用上下文管理器（with语句）自动处理连接的打开和关闭。
    """
    
    def __init__(self, db_config):
        """
        初始化数据库管理器
        
        Args:
            db_config (dict): 包含数据库连接信息的字典，必须包含以下键：
                              DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
        """
        self.db_config = db_config
        
    @contextmanager
    def get_connection(self, dictionary=False, connect_timeout=5):
        """
        获取数据库连接的上下文管理器
        
        Args:
            dictionary (bool): 是否返回字典形式的结果，默认为False
            connect_timeout (int): 连接超时时间，默认为5秒
            
        Yields:
            tuple: (connection, cursor) 数据库连接和游标对象
        """
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(
                user=self.db_config["DB_USER"],
                password=self.db_config["DB_PASSWORD"],
                host=self.db_config["DB_HOST"],
                port=self.db_config["DB_PORT"],
                database=self.db_config["DB_NAME"],
                connect_timeout=connect_timeout
            )
            cursor = connection.cursor(dictionary=dictionary)
            yield connection, cursor
        except mysql.connector.Error as err:
            if connection and connection.is_connected():
                connection.rollback()
            raise err
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                
    def execute_query(self, query, params=None, dictionary=False, commit=False):
        """
        执行查询并返回结果
        
        Args:
            query (str): SQL查询语句
            params (dict, optional): 查询参数
            dictionary (bool): 是否返回字典形式的结果，默认为False
            commit (bool): 是否提交事务，默认为False
            
        Returns:
            list: 查询结果列表
        """
        with self.get_connection(dictionary=dictionary) as (connection, cursor):
            cursor.execute(query, params or {})
            if commit:
                connection.commit()
            return cursor.fetchall()
            
    def execute_update(self, query, params=None):
        """
        执行更新操作（INSERT, UPDATE, DELETE等）
        
        Args:
            query (str): SQL更新语句
            params (dict, optional): 更新参数
            
        Returns:
            int: 受影响的行数
        """
        with self.get_connection() as (connection, cursor):
            cursor.execute(query, params or {})
            connection.commit()
            return cursor.rowcount
            
    def execute_many(self, query, params_list):
        """
        批量执行SQL语句
        
        Args:
            query (str): SQL语句模板
            params_list (list): 参数列表
            
        Returns:
            int: 受影响的行数
        """
        with self.get_connection() as (connection, cursor):
            cursor.executemany(query, params_list)
            connection.commit()
            return cursor.rowcount
