import requests
import random
import time
import sys
import os

# ✅ 实时输出日志
print = lambda *args, **kwargs: __builtins__.print(*args, **{**kwargs, "flush": True})

# ✅ 从环境变量读取 Token
CF_ACCOUNTS = [
    {
        "token": os.getenv("CF_TOKEN_1"),
        "domains": ["2.c.4.f.0.7.4.0.1.0.0.2.ip6.arpa","3.c.4.f.0.7.4.0.1.0.0.2.ip6.arpa"]
    },
    {
        "token": os.getenv("CF_TOKEN_2"),
        "domains": ["e.5.9.f.0.7.4.0.1.0.0.2.ip6.arpa","a.a.9.d.0.7.4.0.1.0.0.2.ip6.arpa"]
    },
    {
        "token": os.getenv("CF_TOKEN_3"),
        "domains": ["6.b.9.d.0.7.4.0.1.0.0.2.ip6.arpa","e.a.9.d.0.7.4.0.1.0.0.2.ip6.arpa"]
    },
    {
        "token": os.getenv("CF_TOKEN_4"),
        "domains": ["5.b.a.f.0.7.4.0.1.0.0.2.ip6.arpa","a.3.8.f.f.f.0.7.0.0.6.2.ip6.arpa"]
    },
    {
        "token": os.getenv("CF_TOKEN_5"),
        "domains": ["3.8.1.8.0.7.4.0.1.0.0.2.ip6.arpa","4.a.8.4.0.7.4.0.1.0.0.2.ip6.arpa"]
    },
    {
        "token": os.getenv("CF_TOKEN_6"),
        "domains": ["c.9.0.4.0.7.4.0.1.0.0.2.ip6.arpa","c.9.8.4.0.7.4.0.1.0.0.2.ip6.arpa"]
    },
    {
        "token": os.getenv("CF_TOKEN_7"),
        "domains": ["1.b.1.8.0.7.4.0.1.0.0.2.ip6.arpa","2.b.1.8.0.7.4.0.1.0.0.2.ip6.arpa"]
    }    
]

IP_LIST_FILE = "./output/data/zx443.txt"
SUBDOMAIN_PREFIX = "hao"
TTL = 120
PROXIED = False
RECORDS_PER_DOMAIN = 4  # 每个域名保持4条A记录

def get_random_ips(ip_file, count):
    with open(ip_file, "r") as f:
        ips = [line.strip() for line in f if line.strip()]
    if len(ips) < count:
        raise Exception(f"IP数量不足，需要 {count} 条，实际只有 {len(ips)} 条")
    return random.sample(ips, count)

def get_zone_id(domain, token):
    if not token:
        raise Exception(f"⚠️ 未检测到 {domain} 的 Cloudflare Token")
    url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    if data["success"] and data["result"]:
        return data["result"][0]["id"]
    else:
        raise Exception(f"获取域名 {domain} 的 Zone ID 失败: {data}")

def get_existing_a_records(zone_id, subdomain, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={subdomain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    if data["success"]:
        return data["result"]
    else:
        return []

def delete_record(zone_id, record_id, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.delete(url, headers=headers)
    r.raise_for_status()
    data = r.json()
    if data["success"]:
        print(f"✅ 删除记录成功: {record_id}")
    else:
        print(f"❌ 删除记录失败: {record_id}, 详情: {data}")

def add_a_record(zone_id, subdomain, ip, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"type": "A", "name": subdomain, "content": ip, "ttl": TTL, "proxied": PROXIED}
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    data = r.json()
    if data["success"]:
        print(f"✅ 添加成功: {subdomain} -> {ip}")
    else:
        print(f"❌ 添加失败: {subdomain} -> {ip}, 详情: {data}")

def main():
    for account in CF_ACCOUNTS:
        token = account["token"]
        for domain in account["domains"]:
            subdomain = f"{SUBDOMAIN_PREFIX}.{domain}"

            print(f"\n=== 🔹 开始处理 {subdomain} ===")

            try:
                zone_id = get_zone_id(domain, token)
                print(f"✅ 获取 Zone ID 成功: {zone_id}")
            except Exception as e:
                print(f"❌ 获取 Zone ID 失败: {e}")
                continue

            existing_records = get_existing_a_records(zone_id, subdomain, token)
            for rec in existing_records:
                delete_record(zone_id, rec["id"], token)
                time.sleep(0.2)

            try:
                ips_to_add = get_random_ips(IP_LIST_FILE, RECORDS_PER_DOMAIN)
                print(f"📦 随机选择 IP: {ips_to_add}")
            except Exception as e:
                print(e)
                continue

            for ip in ips_to_add:
                try:
                    add_a_record(zone_id, subdomain, ip, token)
                    time.sleep(0.2)
                except Exception as e:
                    print(f"添加 {subdomain} -> {ip} 失败: {e}")

if __name__ == "__main__":
    main()
