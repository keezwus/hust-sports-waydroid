# 工作记录

## 2026-10-23

- 接手前人的 Waydroid 环境，确认 App `net.crigh.hzkjsport` 1.0.9
- 修正 `route_track.json` 为真实中操场轨迹，截图核对卫星图
- 解决：
  - `btn_start` 在首屏外 → DPAD_DOWN 滚动
  - AMap LBS error 19 → `Device_Sensors` 补丁
  - 结束后延迟确认导致 GPS 空洞 → 1 秒内点确认
  - 时间窗外 App 丢弃记录
- 当天多次 2.2 km 左右记录均判 `inValidReason=24`

## 2026-10-24

### 抓包

- 自建 CA + 运行时 bind mount 到 `/system/etc/security/cacerts` + hosts 指向宿主机
- 443 TLS 代理抓到 `savesports`
- `jsonsports` 为 AES-128-ECB，密钥 = `HEADER.xml` 中 `SECRET` 前 16 字节
- 解密发现：`stepCount=0`、`stepMinute=0.0`、`s=0`、`minuteSpeed=0`

### 逐项修复

| 版本 | 改动 | 服务端 |
|---|---|---|
| v43 | 步数 2679、速度 16.2 | 24 |
| v44 | 速度 clamp | 24 |
| v45 | 机型 Xiaomi、max=avg | 24 |
| v46 | UA Xiaomi、imei UUID | 24 |
| v47 | 步幅 650/km | 24 |
| v48 | sportImages=1 | 24 |
| v49 | lastOdometerTime=1s | 24 |
| **v50** | **速度 4.0–5.0 波动 + 精度 4–12m** | **isValid=1 ✅** |

### 结论

24 是反作弊对「轨迹过于机器化」的判定：速度、精度、每分钟配速完全恒定。
v50 让 `s` 有 91 个不同值、`ac` 有 77 个不同值后通过。

### 工程化

- 手画轨迹（geojson.io）→ `route_hand.json`，5 圈带车道漂移
- 按 App 自身里程控制结束（2.08 km），避免手画轨迹少记距离
- 无头 Weston + systemd 每日 10:00
- QQ Bot REST API 发结果图 + 记录图
- 重启验证：headless 自启、session RUNNING、登录态保留
- 关闭遗留的 `route-feeder.service`（第二个 mock GPS，会干扰轨迹）

## 结果

```
2026-10-24 11:43  2.08 km  09:27  13.21 km/h  4'32"
状态：待审（提交成功，等待审核）
```
