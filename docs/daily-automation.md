# 每日自动化

## systemd 单元

| 文件 | 作用 |
|---|---|
| `waydroid-daily.timer` | 每天 10:00 触发 |
| `waydroid-daily.service` | oneshot，执行 `daily_run.sh` |
| `weston-headless.service` | 开机启动无头 Weston + Waydroid session |
| `weston-waydroid.service` | 可见桌面（默认 disabled，修理时用） |

安装：

```bash
mkdir -p ~/.config/systemd/user
cp config/systemd/* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now waydroid-daily.timer weston-headless.service
```

## daily_run.sh

流程：

1. 开日志 `~/tiyu/logs/daily_YYYYMMDD_HHMM.log`
2. 如果 session 不是 RUNNING，`waydroid session start`
3. `adb connect`
4. 跑 `run_guard.py`
5. 非 0 退出则通过 Hermes 发「本次自动跑未完成」

## run_guard.py

1. `ensure_provider()`：创建/启用 mock GPS provider
2. force-stop → 启动 App → 主页
3. `am start SportActivity`（绕过主页 banner 误点）
4. DPAD 滚动 → 开始锻炼 → 自由运动 → 锻炼方式选择
5. 先启动 feeder，等 GPS fix，再点「跑步-男生」
6. 8 秒内没进 `SelfSportActivity` 立即中止
7. 固定跑 560 秒（4.5 m/s，feeder 上限 2.5 km → App 约 2.1 km）
8. 结束 → 1 秒内确认
9. 截图结果页 → QQ
10. 打开课外锻炼 → 向上滚到评分次数卡片 → 截图 → QQ

## 通知配置

`~/.config/tiyu/notify.env`：

```bash
QQ_APP_ID=...
QQ_CLIENT_SECRET=...
QQ_TARGET=qqbot:<openid>
```

`notify_run.sh` 会 source 这个文件；`run_guard.py` 从环境变量读取 `QQ_TARGET`，未设置则跳过通知。

QQ 图片通过官方 REST API 发送：

```
POST bots.qq.com/app/getAppAccessToken
POST api.sgroup.qq.com/v2/users/{openid}/files   (file_data base64, file_type=1)
POST api.sgroup.qq.com/v2/users/{openid}/messages (msg_type=7, media.file_info)
```

## 无头 / 桌面切换

```bash
~/tiyu/desktop_on.sh    # 停无头，起可见桌面
~/tiyu/desktop_off.sh   # 停桌面，起无头
```

`start_weston_ui.sh` 与 `start_headless_ui.sh` 都会先 `waydroid session stop`，
保证 session 绑定到新启动的 Wayland socket。

## 重启后的行为

- `weston-headless.service` 开机自启 → session 自动 RUNNING
- `waydroid-daily.timer` 保留，10:00 触发
- 登录态保留在 App 私有目录
- 唯一会失效的情况：在手机端登录，把 VM 的 token 顶掉

## 日志与排查

```bash
journalctl --user -u waydroid-daily.service -n 100
ls -lt ~/tiyu/logs/ | head
tail -f /tmp/guard_*.log
```
