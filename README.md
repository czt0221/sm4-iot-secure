# sm4-iot-secure

基于 Python 的物联网安全通信示例项目，包含设备端 `device` 与服务端 `server` 两部分。项目实现了温度数据采集、基于小时密钥派生的 `SM4-GCM` 加密、UDP 传输、渐进式时间同步、服务端验包解密与防重放处理。

## 项目特点

- 设备端每产生 1 个设备秒，采集 1 条温度数据
- 使用长度为 8 的 FIFO 缓存保存最近采样值
- 当 `timestamp % 8 == 0` 时发送 1 个固定长度 UDP 报文
- 使用 `HMAC-SM3` 按小时派生 `SM4` 会话密钥
- 使用 `SM4-GCM` 对 8 个温度编码值进行认证加密
- 服务端执行时间窗口校验、设备身份校验、防重放校验、解密和落盘
- 设备时钟使用 `pyntp` 参考时间，并通过调整 `clock_rate` 做渐进式同步

## 目录结构

```text
sm4-iot-secure/
├── device/
│   ├── __init__.py
│   ├── main.py
│   ├── sensor/
│   │   ├── __init__.py
│   │   ├── sensor.py
│   │   ├── fake.py
│   │   └── float_to_byte.py
│   ├── encryptor/
│   │   ├── __init__.py
│   │   ├── master_key
│   │   ├── id
│   │   ├── encryptor.py
│   │   ├── random.py
│   │   ├── hmac_sm3.py
│   │   └── sm4_gcm.py
│   └── network/
│       ├── __init__.py
│       ├── network.py
│       ├── send.py
│       ├── udp.py
│       └── time.py
├── server/
│   ├── __init__.py
│   ├── main.py
│   ├── id_masterkey
│   ├── data
│   ├── receive.py
│   ├── udp.py
│   ├── hmac_sm3.py
│   ├── sm4_gcm.py
│   ├── byte_to_float.py
│   ├── database.py
│   └── cache.py
├── pixi.toml
├── pixi.lock
└── README.md
```

## 环境要求

- Windows
- `pixi`
- 可访问 NTP 服务 `pool.ntp.org`

## 环境安装

项目使用 `pixi` 管理运行环境。

```powershell
pixi install
```

安装完成后可直接使用：

```powershell
pixi run server
pixi run device
```

如果需要新增依赖，推荐顺序：

```powershell
pixi add 包名
pixi add --pypi 包名
```

## 配置文件

### device/encryptor/id

设备 ID，支持十进制或带 `0x` 前缀的整数。

示例：

```text
1
```

### device/encryptor/master_key

设备主密钥，使用 16 字节十六进制字符串。

示例：

```text
00112233445566778899AABBCCDDEEFF
```

### server/id_masterkey

服务端维护设备 ID 与主密钥的映射，单行格式如下：

```text
device_id,master_key_hex
```

示例：

```text
1,00112233445566778899AABBCCDDEEFF
```

### server/data

服务端解密并通过校验的数据会追加写入该文件，格式如下：

```text
device_id,timestamp,value
```

同一批次数据按时间升序写入。

## 运行方式

### 启动服务端

```powershell
pixi run server
```

常用示例：

```powershell
pixi run server -- --host 0.0.0.0 --port 9999 --max-time-skew 30
```

参数说明：

- `--host`：UDP 监听地址
- `--port`：UDP 监听端口
- `--server-dir`：服务端配置与数据目录，默认 `server/`
- `--max-time-skew`：允许的时间误差秒数，默认 `30`
- `--replay-ttl`：防重放缓存保留时间，默认 `max(10, 2 * max-time-skew)`
- `--log-level`：日志级别

### 启动设备端

```powershell
pixi run device
```

常用示例：

```powershell
pixi run device -- --host 127.0.0.1 --port 9999 --sync-interval 60
```

参数说明：

- `--host`：服务端地址
- `--port`：服务端 UDP 端口
- `--sync-interval`：时间同步间隔，默认 `60`
- `--device-dir`：设备配置目录，默认 `device/encryptor/`
- `--log-level`：日志级别

## 系统流程

### 设备端

1. 启动后先执行 NTP 初始化同步
2. 设备内部维护 `local_time`、`clock_rate`、`offset_estimate`
3. 每跨过 1 个设备秒边界，生成 1 条温度数据
4. 将温度编码后放入 FIFO 缓存
5. 当 `timestamp % 8 == 0` 时：
   - 取最近 8 条数据
   - 不足 8 条使用 `0xFFFF` 补齐
   - 使用小时密钥执行 `SM4-GCM` 加密
   - 按固定 48 字节格式发送 UDP 报文

### 服务端

1. 接收固定长度 UDP 报文
2. 校验时间误差与 `timestamp % 8 == 0`
3. 校验设备 ID 是否存在
4. 检查 `(id, timestamp)` 是否命中防重放缓存
5. 派生小时密钥并验证 GCM tag
6. 解密得到 8 个温度编码值
7. 还原为 `t, t-1, ..., t-7` 对应时间点
8. 过滤 `0xFFFF`
9. 按时间升序写入 `server/data`

## 协议说明

### 温度编码

- 类型：`uint16`
- 字节序：big-endian
- 编码公式：

```text
encoded = int((value + 99.9) * 10)
```

- 编码范围：
  - `0x0000 -> -99.9`
  - `0x07CF -> 99.9`
- `0xFFFF` 表示 padding

### 时间戳

- 类型：`uint32`
- 单位：秒
- 来源：设备内部单调递增时间

### 明文结构

- 共 16 字节
- 包含 8 个温度编码值，每个值 2 字节

### AAD

- 8 字节
- 结构：`id(4B) + timestamp(4B)`
- 字节序：big-endian

### UDP 报文结构

```text
[0:4]   timestamp   uint32
[4:8]   id          uint32
[8:24]  ciphertext  16B
[24:36] tag         12B
[36:48] iv          12B
```

总长度固定为 48 字节。

## 密钥与加密

### 小时密钥派生

设备与服务端均按以下公式派生小时密钥：

```text
hour_index = timestamp // 3600
hour_key = HMAC-SM3(master_key, hour_index)
```

实现中取 `HMAC-SM3` 输出的前 16 字节作为 `SM4` 密钥。

### 加密参数

- 算法：`SM4-GCM`
- IV 长度：12 字节
- Tag 长度：12 字节
- 所有随机数均使用 `os.urandom`

## 时间同步说明

设备端不会直接把系统时间当作业务时间使用，而是维护独立的本地时钟：

- `local_time`：设备本地时间
- `clock_rate`：时间推进速率
- `offset_estimate`：与参考时间的偏移估计
- `initialized`：是否完成初始同步

同步策略如下：

- 启动阶段阻塞调用 `pyntp`，直到成功获取参考时间
- 初始化完成后，设备时间只通过内部推进更新
- 每隔 `sync_interval` 秒尝试获取新的参考时间
- 使用指数平滑更新 `offset_estimate`
- 根据偏移调整 `clock_rate`
- 将 `clock_rate` 限制在 `[0.9, 1.1]`
- 同步失败时仅输出 warning，不中断采样与发送

## 日志说明

设备端发送日志示例：

```text
sent packet timestamp=1775822528 samples=2 padded=6
```

含义如下：

- `samples`：本次真实采样条数
- `padded`：为凑满 8 条而补入的 `0xFFFF` 数量

## 当前实现说明

- 服务端时间误差默认放宽为 30 秒，便于本地联调
- 防重放缓存 TTL 默认与时间误差联动
- 服务端数据存储使用文本文件，适合课程项目演示与检查

如果需要更严格贴近题面，可在启动服务端时设置：

```powershell
pixi run server -- --max-time-skew 5 --replay-ttl 10
```

## 已验证内容

- `device/` 与 `server/` 模块可以正常编译
- 设备端报文可被服务端正确解析与解密
- UDP 报文长度固定为 48 字节
- 服务端可正确过滤 padding 并按时间升序写入数据
- 设备时钟可连续推进并执行周期同步
