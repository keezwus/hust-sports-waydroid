# HUST Sports Waydroid Autopilot

在 Linux（Debian + Waydroid）上自动完成华中科技大学「创高体育」课外锻炼（跑步-男生），并把记录与审核状态通过 QQ 发到手机。


> 本项目仅用于个人学习与自动化研究。请遵守学校体育考核规定，使用自己账号，风险自负。

## 它能做什么

- 按真实操场轨迹模拟跑步（`route_feeder.py` 通过 mock GPS 推点）
- 自动导航 App：开始锻炼 → 自由运动 → 跑步-男生 → 结束 → 确认
- 自动上传，识别服务端返回（有效 / 无效 / 数据异常）
- 每天 10:00 由 systemd timer 自动跑一次
- 跑完通过 QQ 机器人发送：结果页截图 + 本学期评分次数截图
- 无头运行，不占桌面资源；需要修理时一条命令切回可见桌面

## 已实现的结果

| 项目 | 结果 |
|---|---|
| 单次距离 | 2.0–2.2 km（男生要求 ≥2.0） |
| 配速 | 约 3'50"–4'30"/km（要求 3'20"–10'00"） |
| 服务端 | `isValid=1`，状态「待审（提交成功，等待审核）」 |
| 反作弊 | 关键在速度/精度不能恒定，见 [docs/anti-cheat.md](docs/anti-cheat.md) |

## 架构

```
systemd timer (10:00)
   └─ daily_run.sh
        └─ run_guard.py
             ├─ route_feeder.py  → adb shell cmd location ...   (mock GPS，1 Hz)
             ├─ adb input / uiautomator                         (UI 自动化)
             ├─ screencap                                       (结果 / 记录截图)
             └─ notify_run.sh → QQ Bot API                      (图片 + 文字)
```

Waydroid 运行在 Weston headless 合成器里；adb 负责输入和截图，不需要可见桌面。

## 依赖

- Debian 12（或同类）虚拟机
- [Waydroid](https://docs.waydroid.org/)（LineageOS 13 / Android 13 镜像）
- `adb`、`python3`
- systemd 用户实例（`loginctl enable-linger $USER`）
- 可选：Hermes 网关 + QQ 机器人（用于通知；不配也能跑，只是不发消息）

```bash
sudo apt install adb python3
# Waydroid 按官方文档安装并初始化：
#   waydroid init
#   systemctl enable --now waydroid-container
```

## 快速开始

### 1. 安装 APK

从 [Releases](https://github.com/keezwus/hust-sports-waydroid/releases) 下载 `hust-sports-v51.apk`，校验后安装：

```bash
sha256sum -c hust-sports-v51.apk.sha256
adb install -r hust-sports-v51.apk
```

APK 基于官方 **1.0.9** 修改，补丁说明见 [docs/apk-patching.md](docs/apk-patching.md)。

### 2. 部署脚本

```bash
mkdir -p ~/tiyu
cp -r scripts/* ~/tiyu/
cp config/routes/*.json ~/tiyu/
chmod +x ~/tiyu/*.sh
```

### 3. 配置通知（可选）

```bash
mkdir -p ~/.config/tiyu
cp config/notify.env.example ~/.config/tiyu/notify.env
chmod 600 ~/.config/tiyu/notify.env
# 填入 QQ_APP_ID / QQ_CLIENT_SECRET / QQ_TARGET
```

`QQ_TARGET` 形如 `qqbot:<你的 openid>`。不配置时脚本会跳过通知。

### 4. 安装 systemd 单元

```bash
mkdir -p ~/.config/systemd/user
cp config/systemd/*.service config/systemd/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now waydroid-daily.timer
```

默认每天 **10:00** 触发。无头显示由 `weston-headless.service` 负责，开机自启。

### 5. 首次登录

```bash
~/tiyu/desktop_on.sh     # 切到可见桌面
# 在 Weston 窗口里登录（智慧华中大统一身份认证）
~/tiyu/desktop_off.sh    # 登录完成后切回无头
```

登录态保存在 App 私有目录；**在手机端登录会把 VM 的 token 顶掉**，需要重新登录。

### 6. 体检 & 手动跑一次

```bash
~/tiyu/check.sh                       # 会话、adb、登录态、GPS、时间窗
systemctl --user start waydroid-daily.service   # 立刻跑一轮（约 10 分钟）
```

## 目录

```
docs/            架构、反作弊、每日自动化、改包、工作记录、FAQ
scripts/         feeder / runner / notify / display / routes / build
config/routes/   轨迹 JSON（手画轨迹、椭圆、标准 400m 跑道）
config/systemd/  daily timer、headless、可见桌面
patches/         smali 补丁说明与改包脚本
analysis/        服务端返回码与有效响应样例
```

## 隐私

仓库不包含任何截图或图片，避免个人信息进入版本历史。

## 已知限制

- 记录提交后是「待审」，不是即时有效；审核由学校完成
- 只在 **06:00–23:00** 时间窗内有效
- 手机端登录会挤掉 VM 登录态
- 仅适配 App 1.0.9；升级后补丁需重做
- 不同操场/机型可能需要重新画轨迹

## 免责声明

见 [DISCLAIMER](DISCLAIMER)。代码 MIT；APK 为修改版第三方应用，仅限个人使用，请勿公开分发。
