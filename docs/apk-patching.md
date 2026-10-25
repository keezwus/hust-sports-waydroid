# APK 修改说明

## 目标

官方 1.0.9 在 Waydroid 上有三个问题：

1. AMap 默认走 LBS，模拟器上报 error 19，GPS 不可用
2. 没有计步传感器 → `stepCount=0`、`stepMinute=0.0`
3. mock 定位没有 speed → 每点 `s=0`，`minuteSpeed`、`maxSpeedPerHour` 全 0

## 改包流水线

```bash
# 1. 反编译
java -jar apktool_3.0.3.jar d original.apk -o apktool-out

# 2. 改 smali（patches/ 目录）
# 3. 回编译
java -jar apktool_3.0.3.jar b apktool-out -o full.apk

# 4. 只把 classes5.dex 塞回官方已签名 APK
#    （保留 libChingoSecurity.so 与资源，减少崩溃）
# 5. zipalign + apksigner（debug keystore）
python3 patches/build_apk.py --base original.apk --decoded apktool-out --tag v51
```

`build_apk.py` 会输出 `hust-sports-<tag>.apk`。

## 补丁清单

### 1. AMap 使用 Device_Sensors

`classes3` 中把默认定位模式从 `Hight_Accuracy` 改为 `Device_Sensors`，
并跳过 mock 分支，避免 error 19。

### 2. 步数

`UploadJsonSports.build()` 中若 `stepCount == 0`，用 `odometer`（公里字符串）计算：

```
stepCount = (int)(Double.parseDouble(odometer) * 650)
```

650 步/公里 ≈ 1.54 m 步幅，与 170 步/分的 `stepMinute` 保持一致。

> 注意：不要直接在 `build()` 里插 wide 寄存器代码，会触发
> `VerifyError: Invalid reg type for array index`。把计算放进独立静态方法
> `stepsFromKm(String)I`，在 `build()` 里只调用它。

### 3. 步频

`SportBean.getStepMinute()`：当字段为空或 `"0.0"` 时返回 `"170.0"`。

### 4. 速度

`AMAPLocationService_$...` 中读取 `AMapLocation.getSpeed()` 的位置改成：

```smali
invoke-static {}, Lnet/crigh/cgsport/mysport_/AMAPLocationService_;->fakeSpeed()F
move-result p1
float-to-double v1, p1
```

`fakeSpeed()`：

```
4.5 + 0.5 * sin(now_ms / 10000.0)
```

即 4.0–5.0 m/s、周期约 63 秒。**这是过审的关键**：恒定速度会被判 24。

### 5. 速度上下限

`UploadJsonSports.build()` 中把 `maxSpeedPerHour` 钳到 ≤18、`minSpeedPerHour` 钳到 ≥6，
并把 `maxSpeedPerHour` 覆盖为 `avgSpeed`（避免抖动造成的 25+ 峰值）。

### 6. 设备信息

- `phoneVersion` 固定为 `2201123C,33,13|1.0.9`
- `BaseApplication.setUserAgent()` 的 `Build.MANUFACTURER` 改为 `Xiaomi`
- `imei` 头固定为合法 UUID（Waydroid 的 androidId 哈希为 0，原值为全 0）

### 7. 其它

- 去掉强制 `sportImages="1"`（不需要照片）
- `SportBean.getLastOdometerTime()` 固定 `"00:00:01"`
- 运行开始创建 `/storage/emulated/0/sensor/<uuid>.txt`（App 启动检查）

## 已知坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 点结束就闪退 | smali 寄存器冲突，`VerifyError` | 用独立静态方法，不在大方法里插 wide 运算 |
| 上传 stepCount 仍 0 | `SportBean.dllc` 在 build 时为空 | 改用 `UploadJsonSports.odometer` |
| 服务端 24 | 速度/精度恒定 | 改 `fakeSpeed()` + feeder 精度随机 |
| 桌面光标消失 | Weston 客户端不设置 cursor | 用无头模式；需要桌面时切 `desktop_on.sh` |
