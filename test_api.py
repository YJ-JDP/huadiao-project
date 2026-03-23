import requests
import json

# 替换成你自己的！bce-v3/ALTAK-XTPpqx5tiuy9QqCvh9U8b/76cf1ea7a1a5fd1cdeec08f4dac4d88809aaafed
API_KEY = ""
SECRET_KEY = "Yjj26342634"

def get_access_token():
    """
    获取百度 API 的 access_token
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": SECRET_KEY
    }
    
    try:
        response = requests.post(url, params=params, timeout=10)
        result = response.json()
        print("获取 token 返回:", result)  # 调试用
        return result.get("access_token")
    except Exception as e:
        print(f"获取 token 失败: {e}")
        return None

if __name__ == "__main__":
    token = get_access_token()
    if token:
        print(f"✅ access_token 获取成功！\n{token[:50]}...")
    else:
        print("❌ 获取失败，检查 API Key 和 Secret Key 是否正确")