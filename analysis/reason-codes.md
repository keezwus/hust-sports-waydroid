# 服务端返回码

## 接口

```
POST /cgapp-server/api/l/v7/prejudgment   # 跑前：距离/时间窗等条件
POST /cgapp-server/api/l/v7/savesports    # 结束后：上传记录并判定
```

## savesports 返回

```json
{
  "code": 200,
  "data": {
    "sportId": "...",
    "checkStatus": "-2",
    "inValidReason": "24",
    "isValid": "-1",
    "tip": "数据异常",
    "checkResult": ""
  },
  "message": "OK"
}
```

| 字段 | 说明 |
|---|---|
| `isValid` | `1` 提交成功，`-1` 无效 |
| `checkStatus` | `0` 待审，`-2` 自动判定失败 |
| `inValidReason` | 失败原因码 |
| `tip` | 给用户看的文本 |

## 原因码

| 代码 | tip | 含义 |
|---|---|---|
| 空 | 提交成功，待审核 | 通过 |
| `1` | 未达到指定公里数 | 距离不足 2.0 km |
| `24` | 数据异常 | 综合反作弊（速度/精度/轨迹过于机器化） |

## 通过样例

见 `valid-response-v50.json`。
