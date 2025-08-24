import mss
import base64
import asyncio
import aiohttp
import cv2
import numpy as np
import keyboard
from datetime import datetime
import sys
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()

# 获取 API_KEY
api_key = os.getenv("API_KEY")
ROI = {"left": 543, "top": 1094, "width": 1943-543, "height": 1336-1094}
API_KEY = api_key
API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
LOG_FILE = "log.txt"

def capture_roi():
    """截取 ROI 并返回 base64 图片，同时保存截图"""
    with mss.mss() as sct:
        img = sct.grab(ROI)
        np_img = np.array(img)[:, :, :3]  # 去掉 alpha
        file_name = f"screenshots/roi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        cv2.imwrite(file_name, cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR))
        with open(file_name, "rb") as f:
            image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return image_b64, file_name

async def query_llm(session, image_b64):
    """请求 Doubao LLM"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "doubao-seed-1-6-vision-250815",
        "messages": [
            {
                "content": [
                    {"image_url": {"url": f"data:image/png;base64,{image_b64}"}, "type": "image_url"},
                    {"text": "请提取图片中的日语，并用以下格式解析：\n1. 原文\n2. 生词解释（最多5个）\n3. 难句拆解（最多2句）\n4. 翻译（简洁版）", "type": "text"}
                ],
                "role": "user"
            }
        ]
    }
    async with session.post(API_URL, headers=headers, json=payload) as resp:
        r = await resp.json()
        if resp.status != 200:
            return f"请求失败: {r.get('error', {}).get('message', '未知错误')}"
        return r["choices"][0]["message"]["content"]

def write_log(file_name, result):
    """写入日志到按日期命名的文件"""
    # 确保 logs 文件夹存在
    os.makedirs("logs", exist_ok=True)
    
    # 根据启动时的日期命名日志文件
    log_file = f"logs/log_{datetime.now().strftime('%Y%m%d')}.txt"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Screenshot: {file_name}\n")
        f.write(result + "\n")
        f.write("="*50 + "\n")

async def listener():
    """监听键盘，当按下 + 时执行截图+解析"""
    async with aiohttp.ClientSession() as session:
        print("👉 按下 + 键即可截屏并解析日语（按 Esc 退出）")
        while True:
            if keyboard.is_pressed('+'):
                print("\n[检测到 + 键] 截图并发送请求...")
                img_b64, file_name = capture_roi()
                result = await query_llm(session, img_b64)
                print("\n=== 解析结果 ===\n", result)
                write_log(file_name, result)
                await asyncio.sleep(0.5)
            elif keyboard.is_pressed('esc'):
                print("退出程序")
                break
            await asyncio.sleep(0.05)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    # 创建 screenshots 文件夹（如果不存在）
    os.makedirs("screenshots", exist_ok=True)
    asyncio.run(listener())

if __name__ == "__main__":
    main()
