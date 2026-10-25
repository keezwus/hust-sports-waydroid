# 架构

## 组件

| 组件 | 作用 |
|---|---|
| `weston-headless` | 无头 Wayland 合成器，给 Waydroid 提供显示，不占用 X11 桌面 |
| `waydroid-container` / `session` | Android 13 运行环境 |
| `hust-sports-v51.apk` | 修改版 App：补上步数/步频/速度、修设备指纹 |
| `route_feeder.py` | mock GPS 喂点：沿轨迹 1 Hz 推坐标，速度 4.0–5.0 m/s 波动，精度 4–12 m 随机 |
| `run_guard.py` | UI 自动化 + 结束/确认 + 截图 + 通知 |
| `daily_run.sh` | systemd 入口：检查会话 → 跑 `run_guard.py` → 失败发通知 |
| `notify_run.sh` + `qq_send_image.py` | 通过 QQ Bot REST API 发图片 |
| `tls_proxy.py` | 可选：抓包/解密用的 TLS 中间人（日常不需要） |

## 数据流

```
10:00 timer
  → daily_run.sh
      → 确保 Waydroid session RUNNING
      → adb connect
      → run_guard.py
          → route_feeder.py（后台）
              → adb shell cmd location providers set-test-provider-location gps ...
          → adb shell input tap / keyevent（导航与开始/结束）
          → uiautomator dump（读界面资源 id）
          → App 上传 savesports
          → screencap 结果页
          → notify_run.sh → QQ API（结果图）
          → 打开课外锻炼 → 滚到顶部 → screencap（评分次数）
```

## 为什么用 mock GPS 而不是改 App 的坐标

- Android 13 的 `cmd location` 支持 `add-test-provider` / `set-test-provider-location`，但**不支持 speed**
- App 的 `Location.getSpeed()` 因此为 0，上传的 `s`、`minuteSpeed`、`maxSpeedPerHour` 全是 0
- 所以 APK 里把读取速度的地方改成随时间波动的 `fakeSpeed()`（见 [apk-patching.md](apk-patching.md)）

## 显示模式

| 模式 | 服务 | 用途 |
|---|---|---|
| 无头 | `weston-headless.service` | 日常运行，内存约 40 MB，无窗口 |
| 可见桌面 | `weston-waydroid.service` | 登录/排错，需要时手动启动 |

切换：

```bash
~/tiyu/desktop_on.sh    # 无头 → 可见
~/tiyu/desktop_off.sh   # 可见 → 无头
```

两个服务共用一个 `wayland-0` socket，不能同时启动。

## 关键路径

| 内容 | 路径 |
|---|---|
| 脚本 | `~/tiyu/` |
| 轨迹 | `~/tiyu/route_hand.json` |
| 通知配置 | `~/.config/tiyu/notify.env` |
| 日志 | `~/tiyu/logs/daily_*.log`、`/tmp/guard_*.log` |
| systemd 用户单元 | `~/.config/systemd/user/` |
