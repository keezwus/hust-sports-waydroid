# FAQ

## 记录一直是「待审」正常吗？

正常。提交成功是 `isValid=1`，学校审核后才变成「有效」。本工具只负责提交。

## 为什么第二天没跑？

依次检查：

```bash
systemctl --user status waydroid-daily.timer
systemctl --user status waydroid-daily.service
journalctl --user -u waydroid-daily.service -n 100
```

常见原因：

- 手机端登录把 VM 的 token 顶掉 → App 停在登录页
- Waydroid session 没起来
- 时间窗外（06:00–23:00）

## 登录页出现了怎么办？

```bash
~/tiyu/desktop_on.sh    # 打开可见桌面
# 登录
~/tiyu/desktop_off.sh   # 切回无头
```

## 桌面鼠标消失 / 黑屏？

Weston 的 X11 后端在客户端不设置 cursor 时会隐藏光标。日常用无头模式；
需要桌面时 `desktop_on.sh`，它会重启 session 并重新挂 UI。

## 提示「数据异常」（24）

说明轨迹被判定过于机器化。确认：

- `route_feeder.py` 的速度波动与精度随机是否生效
- 是否只有一条恒定速度的旧 feeder 在运行（`pgrep -af route_feeder`）

## 距离不足 2.0

手画轨迹会被 App 少记 10–15%。把 feeder 上限从 2.5 km 提到 2.6–2.7 km，
或在 `run_guard.py` 里把结束时间从 560 秒加长。

## 会封号吗？

工具只提交正常跑步数据，但使用自动化本身可能违反学校规定。
请自行评估风险，建议只在自己的账号上低频使用。

## 换个操场怎么改轨迹？

1. 在 https://geojson.io 沿跑道画一条线，导出 GeoJSON
2. `python3 route_from_geojson.py drawn.geojson route_drawn.json`
3. `python3 make_multilap.py route_drawn.json route_hand.json --distance 2000`
4. 把 `route_hand.json` 放到 `~/tiyu/`
