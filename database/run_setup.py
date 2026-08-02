import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

ca_path = os.path.join(os.path.dirname(__file__), "..", "ca.pem")

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    cursorclass=pymysql.cursors.DictCursor,
    ssl={"ca": ca_path},
)

try:
    with conn.cursor() as cur:
        # Table creation scripts
        # We omit CREATE DATABASE and USE because we are already connected to MYSQL_DATABASE (defaultdb)
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(sql)
        
        sql = """
        CREATE TABLE IF NOT EXISTS reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            topic VARCHAR(255) NOT NULL,
            report_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(512) NOT NULL,
            file_type ENUM('docx', 'pdf') NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
        cur.execute(sql)
        
    conn.commit()
    print("Tables created successfully in defaultdb.")
finally:
    conn.close()