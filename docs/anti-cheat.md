# 反作弊分析：为什么一直「数据异常」

## 服务端返回码

`POST /cgapp-server/api/l/v7/savesports` 返回：

```json
{"code":200,"data":{"isValid":"-1","inValidReason":"24","tip":"数据异常"}}
```

| inValidReason | tip | 含义 |
|---|---|---|
| `1` | 未达到指定公里数 | 距离 < 2.0 km |
| `24` | 数据异常 | 综合反作弊（本次卡住的地方） |

`isValid=1` + `checkStatus=0` + `tip=提交成功，待审核` 才是通过。

## 排查过程（2026-10-24 上午）

每一轮都是 2.0 km 以上、配速合规，变量只改一处：

| 版本 | 改动 | 结果 |
|---|---|---|
| v43 | `stepCount` 2679、速度 16.2、`stepMinute` 170 | 24 |
| v44 | 最大/最小速度钳到 18/6 | 24 |
| v45 | `phoneVersion` 改 Xiaomi、max=avg | 24 |
| v46 | UA 改 Xiaomi、imei 改固定 UUID | 24 |
| v47 | 步幅 650/km（步数 1313） | 24 |
| v48 | `sportImages=1` | 24 |
| v48b | 速度正弦变化（只改 feeder） | 24 |
| v49 | `lastOdometerTime=00:00:01` | 24 |
| **v50** | **速度 4.0–5.0 m/s 波动 + 精度 4–12 m 随机** | **isValid=1 ✅** |

## 结论

服务端不是判步数、机型、IMEI、照片，而是判**轨迹过于机器化**：

- v49 之前：每个点的 `s` 恒定 16.2，`ac` 恒定 5.0，每分钟配速完全一样
- v50：`s` 有 91 个不同值（14.4–17.9），`ac` 有 77 个不同值（4–12），`minuteSpeed` 逐分钟变化

解密后的 v50 payload：

```json
{
  "stepCount": 1319,
  "stepMinute": "170.0",
  "avgSpeed": "15.66",
  "maxSpeedPerHour": "15.66",
  "minSpeedPerHour": "6.0",
  "minuteSpeed": [{"min":"1","v":"17.1"},{"min":"2","v":"17.35"}],
  "coordinate": [{"s": 14.4, "ac": 4.0, ...}, ...]
}
```

## 实践建议

1. 速度不要恒定：4.0–5.0 m/s 缓慢波动（周期约 1 分钟）
2. GPS 精度不要恒定：4–12 m 随机
3. 距离留余量：目标 2.0 km 时实际跑 2.05–2.10 km（App 计程会因轨迹形状少记 10–15%）
4. 轨迹不要用完美椭圆；手画轨迹 + 每圈车道漂移 + 噪声更像真人
5. 06:00–23:00 之外不要跑，客户端会直接丢弃

## 抓包方法（可选）

日常不需要；仅用于分析时：

- 自建 CA，运行时 bind mount 到 `/system/etc/security/cacerts`
- `/system/etc/hosts` 把 `petzjk.hust.edu.cn` 指到宿主机
- 宿主机 443 跑 `tls_proxy.py`
- App 的 `jsonsports` 是 AES-128-ECB，密钥是 `shared_prefs/HEADER.xml` 中 `SECRET` 字符串前 16 字节

> 抓包文件含 JWT/secret/imei，不要提交到仓库。
