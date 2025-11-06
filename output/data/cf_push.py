#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import random
import time

# ========== 配置（根据你的实际需要可调整） ==========
CF_ACCOUNTS = [
    {
        "token_env": "CF_TOKEN_1",
        "domains": [
            "2.c.4.f.0.7.4.0.1.0.0.2.ip6.arpa",
            "3.c.4.f.0.7.4.0.1.0.0.2.ip6.arpa"
        ]
    },
    {
        "token_env": "CF_TOKEN_2",
        "domains": [
            "e.5.9.f.0.7.4.0.1.0.0.2.ip6.arpa",
            "a.a.9.d.0.7.4.0.1.0.0.2.ip6.arpa"
        ]
    },
    {
        "token_env": "CF_TOKEN_3",
        "domains": [
            "6.b.9.d.0.7.4.0.1.0.0.2.ip6.arpa",
            "e.a.9.d.0.7.4.0.1.0.0.2.ip6.arpa"
        ]
    },
    {
        "token_env": "CF_TOKEN_4",
        "domains": [
            "5.b.a.f.0.7.4.0.1.0.0.2.ip6.arpa",
            "a.3.8.f.f.f.0.7.0.0.6.2.ip6.arpa"
        ]
    },
    {
        "token_env": "CF_TOKEN_5",
        "domains": [
            "3.8.1.8.0.7.4.0.1.0.0.2.ip6.arpa",
            "4.a.8.4.0.7.4.0.1.0.0.2.ip6.arpa"
        ]
    }
]

IP_LIST_FILE = os.path.join(os.path.dirname(__file__), "zx443.txt")  # output/data/zx443.txt
SUBDOMAIN_PREFIX = "hao"
TTL = 120
PROXIED = False
RECORDS_PER_DOMAIN = 4
REQUEST_DELAY = 0.25  # 秒，避免短时间内请求过快

# ========== 工具函数 ==========
def read_ip_list(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"IP 列表文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        ips = [line.strip() for line in f if line.strip()]
    return ips

def get_random_ips(ip_file, count):
    ips = read_ip_list(ip_file)
    if len(ips) < count:
        raise Exception(f"IP数量不足，需要 {count} 条，实际只有 {len(ips)} 条")
    return random.sample(ips, count)

def get_zone_id(domain, token):
    # 取 zone 名字的最右两节作为 zone 查询（适用于大多数域名）
    # 对于特殊情况可直接使用完整 zone 名
    url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("success") and data.get("result"):
        return data["result"][0]["id"]
    raise Exception(f"获取域名 {domain} Zone ID 失败: {data}")

def get_existing_a_records(zone_id, subdomain, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={subdomain}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("result", []) if data.get("success", False) else []

def delete_record(zone_id, record_id, token, subdomain, ip):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.delete(url, headers=headers, timeout=15)
    if r.ok:
        print(f"🧹 已删除旧记录: {subdomain} -> {ip} (id={record_id})")
    else:
        print(f"❌ 删除失败: {subdomain} -> {ip} (id={record_id}), 状态: {r.status_code}, 响应: {r.text}")

def add_a_record(zone_id, subdomain, ip, token):
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"type": "A", "name": subdomain, "content": ip, "ttl": TTL, "proxied": PROXIED}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    if r.ok:
        print(f"✅ 添加成功: {subdomain} -> {ip}")
    else:
        # 若 Cloudflare 返回非法头或 token 问题，响应里通常会有提示
        print(f"❌ 添加失败: {subdomain} -> {ip}, 状态: {r.status_code}, 响应: {r.text}")

# ========== 主流程 ==========
def main():
    print("🚀 Cloudflare A 记录推送脚本启动\n")
    # 读取 ip 文件基本检查
    try:
        ips_all = read_ip_list(IP_LIST_FILE)
    except Exception as e:
        print(f"❌ 无法读取 IP 列表: {e}")
        return

    print(f"ℹ️ IP 列表读取成功，共 {len(ips_all)} 条 IP。每个域名将写入 {RECORDS_PER_DOMAIN} 条 A 记录。\n")

    for idx, account in enumerate(CF_ACCOUNTS, start=1):
        token_env = account.get("token_env")
        token = os.getenv(token_env)
        if not token:
            print(f"⚠️ 第 {idx} 组 (env={token_env}) 未检测到 token，跳过该组。")
            continue
        # 仅输出 token 长度以便调试，不打印 token 本体
        print(f"🔐 第 {idx} 组 token 已加载 (长度: {len(token)} 字符)")

        for domain in account.get("domains", []):
            subdomain = f"{SUBDOMAIN_PREFIX}.{domain}"
            print(f"\n🌐 正在处理域名: {subdomain}")

            # 获取 zone id
            try:
                zone_id = get_zone_id(domain, token)
                print(f"🔎 获取 Zone ID 成功: {zone_id}")
            except Exception as e:
                print(f"❌ 获取 Zone ID 失败: {e}")
                continue

            # 列出并删除现有 A 记录
            try:
                existing = get_existing_a_records(zone_id, subdomain, token)
            except Exception as e:
                print(f"❌ 查询现有记录失败: {e}")
                continue

            if existing:
                print(f"ℹ️ 发现 {len(existing)} 条现有 A 记录，开始删除...")
                for rec in existing:
                    try:
                        delete_record(zone_id, rec["id"], token, subdomain, rec.get("content"))
                    except Exception as e:
                        print(f"❌ 删除记录异常: {e}")
                    time.sleep(REQUEST_DELAY)
            else:
                print("ℹ️ 无旧记录，跳过删除。")

            # 选择新 IP 并添加
            try:
                new_ips = random.sample(ips_all, RECORDS_PER_DOMAIN)
            except Exception as e:
                print(f"❌ 从 IP 列表选取失败: {e}")
                continue

            print(f"➕ 开始添加 {len(new_ips)} 条新记录：{', '.join(new_ips)}")
            for ip in new_ips:
                try:
                    add_a_record(zone_id, subdomain, ip, token)
                except Exception as e:
                    print(f"❌ 添加记录异常: {e}")
                time.sleep(REQUEST_DELAY)

            print(f"✅ 完成域名: {subdomain}")

    print("\n🎉 所有任务完成。")

if __name__ == "__main__":
    main()
