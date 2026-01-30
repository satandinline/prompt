"""数据库初始化脚本"""
import mysql.connector
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

#  数据库连接配置
config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE', 'prompt')
}

print(f"正在连接数据库 {config['database']}...")

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    # 读取SQL文件
    sql_file = Path(__file__).parent / 'init_database.sql'
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 分割SQL语句（按照DELIMITER分隔）
    statements = []
    current_statement = []
    delimiter = ';'
    
    for line in sql_content.split('\n'):
        line = line.strip()
        
        # 跳过注释和空行
        if line.startswith('--') or not line:
            continue
            
        # 处理DELIMITER命令
        if line.startswith('DELIMITER'):
            delimiter = line.split()[-1]
            continue
        
        current_statement.append(line)
        
        # 如果行以当前delimiter结尾，执行语句
        if line.endswith(delimiter):
            stmt = ' '.join(current_statement)
            stmt = stmt.rstrip(delimiter)
            
            if stmt.strip():
                try:
                    cursor.execute(stmt)
                    # 消费结果
                    try:
                        cursor.fetchall()
                    except:
                        pass
                    print(f"\u2713 执行成功: {stmt[:50]}...")
                except mysql.connector.Error as e:
                    print(f"\u2717 执行失败: {stmt[:50]}...")
                    print(f"  错误: {e}")
            
            current_statement = []
            delimiter = ';'
    
    conn.commit()
    print("\n数据库初始化完成！")
    
except mysql.connector.Error as e:
    print(f"数据库错误: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
