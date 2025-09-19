import sys
import os
import logging
import traceback
from flask import Flask, request, jsonify
import subprocess
import yaml
from socket import error as socket_error
import socket
import tempfile
import time  # 可选：用于测试延迟

# ------------------ 获取运行路径 ------------------
if getattr(sys, 'frozen', False):
    # 打包模式
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # 源码运行模式
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CWD = os.getcwd()

# ------------------ 日志配置 ------------------
log_dir = os.path.join(BASE_DIR, 'logs')
log_path = os.path.join(log_dir, 'log.txt')
fallback_log_path = os.path.join(tempfile.gettempdir(), 'AiablePCService_log.txt')

os.makedirs(log_dir, exist_ok=True)  # 确保 logs 目录存在

def setup_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    try:
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        logger.info(f"Using log: {log_path}")
    except Exception as e:
        try:
            fallback_handler = logging.FileHandler(fallback_log_path, encoding='utf-8')
            fallback_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(fallback_handler)
            logger.warning(f"Fallback log: {fallback_log_path} (orig error: {str(e)})")
        except:
            logger.warning("No file logging possible")

    return logger

logger = setup_logging()
logger.info(f"Start: args={sys.argv}, BASE_DIR={BASE_DIR}, CWD={CWD}")

# ------------------ 全局异常捕获 ------------------
def log_uncaught_exception(exc_type, exc_value, exc_traceback):
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.error(f"Uncaught: {err_msg}")

sys.excepthook = log_uncaught_exception

# ------------------ 配置加载 ------------------
config_path = os.path.join(BASE_DIR, 'config.yaml')  # 外部可修改
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    logger.info(f"Config loaded from {config_path}")
except Exception as e:
    logger.error(f"Config error: {traceback.format_exc()}")
    sys.exit(1)

SECRET_TOKEN = config.get("token", "")
PORT = config.get("port", 5000)
HOST = config.get("host", "127.0.0.1")
items = config.get("items", [])

# 检查 ID 唯一性
ids = [item['id'] for item in items]
if len(ids) != len(set(ids)):
    logger.error(f"Duplicate IDs: {ids}")
    raise ValueError("Duplicate IDs")

app = Flask(__name__)

def require_token(func):
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Auth-Token")
        if token != SECRET_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

class CommandHandler:
    @staticmethod
    @require_token
    def openfile_handler(file_path, default_args=""):
        try:
            extra_args_list = [str(value) for value in request.args.values()]
            all_args = " ".join([default_args] + extra_args_list).strip()
            cmd = f'start "" "{file_path}" {all_args}'.strip()
            subprocess.Popen(cmd, shell=True)
            logger.info(f"Opened: {file_path} {all_args}")
            return jsonify({"status": f"Opened {file_path} {all_args}"})
        except Exception as e:
            logger.error(f"openfile error: {traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @require_token
    def runcommand_handler(command, default_args=""):
        try:
            extra_args_list = [str(value) for value in request.args.values()]
            all_args = " ".join([default_args] + extra_args_list).strip()
            full_cmd = f"{command} {all_args}".strip()
            output = subprocess.check_output(full_cmd, shell=True, encoding="utf-8")
            logger.info(f"Executed: {full_cmd}")
            return jsonify({"status": "success", "output": output})
        except subprocess.CalledProcessError as e:
            error_msg = e.output if e.output else str(e)
            logger.error(f"cmd error: {error_msg}")
            return jsonify({"error": error_msg}), 500
        except Exception as e:
            logger.error(f"runcommand error: {traceback.format_exc()}")
            return jsonify({"error": str(e)}), 500

    @staticmethod
    def register_routes(app_instance, items_list):
        logger.info("Registering routes...")
        for item in items_list:
            item_type = item.get("type")
            item_id = item.get("id")
            if item_type == "openfile":
                path = item.get("path")
                args = item.get("args", "")
                bound_handler = lambda p=path, a=args: CommandHandler.openfile_handler(p, a)
                app_instance.add_url_rule(f"/{item_type}/{item_id}", f"{item_type}_{item_id}", bound_handler, methods=["GET"])
                logger.info(f"Registered openfile/{item_id}")
            elif item_type == "runcommand":
                cmd = item.get("command")
                args = item.get("args", "")
                bound_handler = lambda c=cmd, a=args: CommandHandler.runcommand_handler(c, a)
                app_instance.add_url_rule(f"/{item_type}/{item_id}", f"{item_type}_{item_id}", bound_handler, methods=["GET"])
                logger.info(f"Registered runcommand/{item_id}")
            else:
                logger.warning(f"Unknown type: {item_type}")
        logger.info("Routes registered.")

def main():
    logger.info("Registering routes...")
    try:
        CommandHandler.register_routes(app, items)
    except Exception as e:
        logger.error(f"Routes error: {traceback.format_exc()}")
        raise

    logger.info(f"Main: binding {HOST}:{PORT}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
        logger.info("Port bound OK")
        # time.sleep(10)  # 可选延迟
        app.run(host=HOST, port=PORT, threaded=True)
    except Exception as e:
        logger.error(f"Main error: {traceback.format_exc()}")
    finally:
        logger.info("Main exit")

if __name__ == '__main__':
    logger.info("Debug mode")
    main()
