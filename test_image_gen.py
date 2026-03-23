from openai import OpenAI

# 你的千帆平台 API Key（从 https://console.bce.baidu.com/qianfan/ais/console/apiKey 获取）
API_KEY = "bce-v3/ALTAK-XTPpqx5tiuy9QqCvh9U8b/76cf1ea7a1a5fd1cdeec08f4dac4d88809aaafed"

client = OpenAI(
    base_url='https://qianfan.baidubce.com/v2',
    api_key=API_KEY
)

def generate_image(prompt, save_path="output.png"):
    """
    使用千帆平台 qwen-image 模型生成图片
    """
    try:
        response = client.images.generate(
            model="qwen-image",  # 使用图像生成模型
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        
        # 返回的是 base64 编码的图片
        image_b64 = response.data[0].b64_json
        if image_b64:
            import base64
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(image_b64))
            print(f"✅ 图片已保存: {save_path}")
            return save_path
        else:
            # 也可能是 URL
            image_url = response.data[0].url
            if image_url:
                import requests
                img_data = requests.get(image_url).content
                with open(save_path, "wb") as f:
                    f.write(img_data)
                print(f"✅ 图片已保存: {save_path}")
                return save_path
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        return None

# 测试
if __name__ == "__main__":
    prompt = "故宫太和殿梁枋上的和玺彩画，金龙纹，金碧辉煌，中国古建筑彩绘，传统工笔风格"
    generate_image(prompt, "test_output.png")