# smali 补丁

按顺序对 apktool 反编译目录修改。类名经过混淆，路径以 `apktool-out/smali_classes*` 为准。

## 1. AMap 走 Device_Sensors

`smali_classes3/com/amap/api/location/...` 中把默认 `Hight_Accuracy` 改为
`Device_Sensors`，并跳过 mock 分支，避免 Waydroid 上 LBS error 19。

## 2. 步数（`UploadJsonSports.smali`）

在 `build()` 里 `stepCount` 赋值后：

```smali
iget v2, p0, Lnet/crigh/cgsport/model/UploadJsonSports;->stepCount:I
if-nez v2, :step_done
iget-object v2, p0, Lnet/crigh/cgsport/model/UploadJsonSports;->odometer:Ljava/lang/String;
invoke-static {v2}, Lnet/crigh/cgsport/model/UploadJsonSports;->stepsFromKm(Ljava/lang/String;)I
move-result v2
iput v2, p0, Lnet/crigh/cgsport/model/UploadJsonSports;->stepCount:I
:step_done
```

新增静态方法（不要内联 wide 运算，否则 `VerifyError`）：

```smali
.method public static stepsFromKm(Ljava/lang/String;)I
    .locals 4
    :try_start_0
    invoke-static {p0}, Ljava/lang/Double;->parseDouble(Ljava/lang/String;)D
    move-result-wide v0
    const-wide v2, 0x4084500000000000L    # 650.0
    mul-double/2addr v0, v2
    double-to-int v0, v0
    return v0
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0
    :catch_0
    const/4 v0, 0x0
    return v0
.end method
```

## 3. 步频（`SportBean.smali`）

```smali
.method public getStepMinute()Ljava/lang/String;
    .locals 2
    iget-object v0, p0, Lnet/crigh/cgsport/model/SportBean;->stepMinute:Ljava/lang/String;
    if-nez v0, :zero
    const-string v1, "0.0"
    invoke-virtual {v0, v1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-nez v1, :ret
    :zero
    const-string v0, "170.0"
    :ret
    return-object v0
.end method
```

## 4. 速度波动（关键）

`AMAPLocationService_$....smali` 中，把

```smali
invoke-virtual {p1}, Lcom/amap/api/location/AMapLocation;->getSpeed()F
move-result p1
```

替换为：

```smali
invoke-static {}, Lnet/crigh/cgsport/mysport_/AMAPLocationService_;->fakeSpeed()F
move-result p1
```

并在 `AMAPLocationService_.smali` 末尾新增：

```smali
.method public static fakeSpeed()F
    .locals 4
    invoke-static {}, Ljava/lang/System;->currentTimeMillis()J
    move-result-wide v0
    long-to-double v0, v0
    const-wide v2, 0x40C3880000000000L    # 10000.0
    div-double/2addr v0, v2
    invoke-static {v0, v1}, Ljava/lang/Math;->sin(D)D
    move-result-wide v0
    const-wide v2, 0x3FE0000000000000L    # 0.5
    mul-double/2addr v0, v2
    const-wide v2, 0x4012000000000000L    # 4.5
    add-double/2addr v0, v2
    double-to-float v0, v0
    return v0
.end method
```

即 `4.5 + 0.5*sin(now_ms/10000)`，4.0–5.0 m/s。

## 5. 速度上下限（`UploadJsonSports.smali`）

新增 `clampMax` / `clampMin` 静态方法，在 `build()` 里对
`maxSpeedPerHour` / `minSpeedPerHour` 调用；随后把 `maxSpeedPerHour`
覆盖为 `avgSpeed`，避免抖动产生 25+ 的峰值。

## 6. 设备信息

```smali
# UploadJsonSports.build()
const-string v1, "2201123C,33,13|1.0.9"
iput-object v1, p0, Lnet/crigh/cgsport/model/UploadJsonSports;->phoneVersion:Ljava/lang/String;

# BaseApplication.setUserAgent()
const-string v0, "Xiaomi"    # 原 sget-object Build;->MANUFACTURER

# imei：把生成 UUID 的方法改成返回固定值
const-string v0, "2f8a1c4e-7b3d-4a59-9c2e-1d6f8b0a3c57"
return-object v0
```

## 7. 其它

- 去掉强制 `sportImages="1"`
- `SportBean.getLastOdometerTime()` 返回 `"00:00:01"`
- 运行开始时创建 `/storage/emulated/0/sensor/<uuid>.txt`

## 构建

```bash
python3 build_apk.py --base original.apk --decoded apktool-out --tag v51
```
