# sm4-iot-secure

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Pixi](https://img.shields.io/badge/Env-pixi-6D28D9)
![Crypto](https://img.shields.io/badge/Crypto-SM4--GCM%20%2B%20HMAC--SM3-0F766E)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-tkinter%20%2B%20tkcalendar-1F2937)

`sm4-iot-secure` 是一个基于 Python 的物联网安全通信示例项目，包含设备端 `device` 与服务端 `server` 两部分。项目聚焦于温度数据的安全传输，实现了设备端采样、`SM4-GCM` 加密、UDP 通信、渐进式时间同步，以及服务端验包、解密、入库和图形化管理。

## 功能概览

- 设备端每生成 1 个设备秒，采集 1 条温度数据
- 使用长度为 8 的 FIFO 缓存保存最近采样值
- 当 `timestamp % 8 == 0` 时发送 1 个固定长度 UDP 报文
- 使用 `HMAC-SM3` 按小时派生 `SM4` 会话密钥
- 使用 `SM4-GCM` 对 8 个温度编码值进行认证加密
- 服务端收到数据后写入本地 SQLite 数据库
- 服务端每次收到 UDP 报文都会动态查询数据库中的设备 ID 和主密钥
- 服务端提供图形化界面，支持数据筛选、设备管理和 SQL 控制台

## 技术栈

- `Python`
- `pixi`
- `cryptography`
- `pyntp`
- `tkinter`
- `tkcalendar`
- `SQLite`

## 快速启动

### 环境要求

- `Windows`
- `pixi`
- 可访问 `pool.ntp.org`

安装环境：

```powershell
pixi install
```

### 启动服务端图形界面

```powershell
pixi run server
```

### 启动设备端

```powershell
pixi run device
```

### 常用启动参数

服务端：

```powershell
pixi run server --host 0.0.0.0 --port 9999 --max-time-skew 30
```

无界面服务端：

```powershell
pixi run server --headless
```

设备端：

```powershell
pixi run device --host 127.0.0.1 --port 9999 --sync-interval 60
```

## 项目结构

```text
sm4-iot-secure/
├── .gitattributes                  # Git 属性配置
├── .gitignore                      # Git 忽略规则
├── pixi.toml                       # pixi 项目配置与任务定义
├── pixi.lock                       # pixi 依赖锁文件
├── README.md                       # 项目说明文档
├── device/                         # 设备端代码
│   ├── __init__.py                 # 设备端包标记
│   ├── main.py                     # 设备端主入口，负责采样、缓存、加密、发送
│   ├── sensor/                     # 传感器模块
│   │   ├── __init__.py             # 传感器子包标记
│   │   ├── sensor.py               # 传感器统一入口
│   │   ├── fake.py                 # 模拟温度数据生成
│   │   └── float_to_byte.py        # 温度浮点值编码为 uint16
│   ├── encryptor/                  # 加密模块
│   │   ├── __init__.py             # 加密子包标记
│   │   ├── id                      # 当前设备 ID 配置文件
│   │   ├── master_key              # 当前设备主密钥配置文件
│   │   ├── encryptor.py            # 加密入口与小时密钥缓存
│   │   ├── random.py               # IV 生成
│   │   ├── hmac_sm3.py             # HMAC-SM3 小时密钥派生
│   │   └── sm4_gcm.py              # SM4-GCM 加密实现
│   └── network/                    # 网络与时间同步模块
│       ├── __init__.py             # 网络子包标记
│       ├── network.py              # 网络模块入口
│       ├── send.py                 # UDP 发送
│       ├── udp.py                  # UDP 报文结构
│       └── time.py                 # 渐进式时间同步与设备时钟
└── server/                         # 服务端代码
    ├── __init__.py                 # 服务端包标记
    ├── main.py                     # 服务端主入口
    ├── gui.py                      # 图形化管理界面
    ├── receive.py                  # UDP 接收、验包、解密、入库流程
    ├── database.py                 # SQLite 数据库访问封装
    ├── cache.py                    # 防重放缓存
    ├── udp.py                      # UDP 报文解析
    ├── hmac_sm3.py                 # HMAC-SM3 小时密钥派生
    ├── sm4_gcm.py                  # SM4-GCM 解密实现
    ├── byte_to_float.py            # uint16 温度值解码
    ├── server.db                   # SQLite 数据库主文件，运行后生成
    ├── server.db-shm               # SQLite 共享内存文件，运行中可能生成
    ├── server.db-wal               # SQLite WAL 日志文件，运行中可能生成
    └── gui_state.json              # GUI 上次筛选与排序状态，运行后生成
```

## 数据库存储

服务端使用本地单文件 `SQLite` 数据库存储设备信息与采集数据：

```text
server/server.db
```

数据库存储方式说明：

- 使用本地单文件数据库
- 不依赖独立数据库服务
- 图形界面、UDP 接收逻辑与 SQL 控制台共用同一个数据库文件

数据库包含两张核心表：

- `devices`
  - 存储设备 ID、主密钥、备注、创建时间
- `measurements`
  - 存储设备 ID、时间戳、温度值、入库时间

时间字段在数据库中保存原始时间戳，界面显示时再格式化为年月日时分秒，便于查询、排序和索引优化。

## 运行参数

### 服务端参数

- `--host`：UDP 监听地址
- `--port`：UDP 监听端口
- `--server-dir`：服务端工作目录，默认 `server/`
- `--max-time-skew`：允许的时间误差秒数，默认 `30`
- `--replay-ttl`：防重放缓存保留时间，默认 `max(10, 2 * max-time-skew)`
- `--log-level`：日志级别
- `--headless`：无界面模式，仅启动 UDP 服务

### 设备端参数

- `--host`：服务端地址
- `--port`：服务端 UDP 端口
- `--sync-interval`：时间同步间隔，默认 `60`
- `--device-dir`：设备配置目录，默认 `device/encryptor/`
- `--log-level`：日志级别

## 服务端图形界面

服务端界面包含三个页面。

### 1. 数据管理

支持以下功能：

- 按设备筛选
- 按时间范围筛选
- 使用小日历选择日期，并通过时、分、秒输入框设置时间
- 按时间戳或温度值排序
- 修改筛选条件后自动刷新结果
- 在相同条件下手动刷新最新入库数据
- 自动记住上一次关闭前的设备筛选与排序状态
- 清空所有采集数据

数据表显示字段：

- 设备 ID
- 备注名
- 格式化时间
- 原始时间戳
- 温度值

### 2. 设备管理

支持以下功能：

- 分配新的设备 ID 与主密钥
- 查看所有已分配设备
- 通过弹窗修改设备备注
- 删除设备及其关联采集数据
- 将选中设备的 `id` 和 `master_key` 直接写入目标设备目录

### 3. SQL 控制台

支持以下功能：

- 在多行输入框中编写 SQL
- 执行 SQL 语句
- 清空当前 SQL 输入
- 在下方日志区查看查询结果、影响行数或错误信息

简单 SQL 示例：

```sql
SELECT id, note, created_at
FROM devices;
```

```sql
SELECT device_id, timestamp, value
FROM measurements
ORDER BY timestamp DESC
LIMIT 20;
```

```sql
SELECT device_id, COUNT(*) AS total
FROM measurements
GROUP BY device_id;
```

```sql
UPDATE devices
SET note = '实验室设备1'
WHERE id = 1;
```

```sql
DELETE FROM measurements
WHERE device_id = 1;
```

## 设备配置与分配

设备端运行依赖以下两个配置文件：

- `device/encryptor/id`
- `device/encryptor/master_key`

服务端可在图形界面中直接分配新设备：

1. 点击“分配新设备”
2. 输入备注，可留空
3. 服务端自动生成新的设备 ID
4. 服务端自动生成 16 字节主密钥
5. 新设备信息写入数据库

设备管理页提供“写入设备目录”按钮。选择目标 `device` 目录后，程序会自动覆盖写入：

- `device/encryptor/id`
- `device/encryptor/master_key`

## 协议说明

### 温度编码

- 类型：`uint16`
- 字节序：`big-endian`
- 编码公式：

```text
encoded = int((value + 99.9) * 10)
```

- 编码范围：
  - `0x0000 -> -99.9`
  - `0x07CF -> 99.9`
- `0xFFFF` 表示 `padding`

### 时间戳

- 类型：`uint32`
- 单位：秒
- 来源：设备内部单调递增时间

### 明文结构

- 总长度 16 字节
- 包含 8 个温度编码值，每个值 2 字节

### AAD

- 总长度 8 字节
- 结构：`id(4B) + timestamp(4B)`
- 字节序：`big-endian`

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

设备端与服务端按以下公式派生小时密钥：

```text
hour_index = timestamp // 3600
hour_key = HMAC-SM3(master_key, hour_index)
```

实现中取 `HMAC-SM3` 输出的前 16 字节作为 `SM4` 密钥。

加密参数如下：

- 算法：`SM4-GCM`
- IV 长度：12 字节
- Tag 长度：12 字节
- 所有随机数均使用 `os.urandom`

## 时间同步

设备端维护独立的本地时钟，而不是直接把系统时间作为业务时间。主要状态包括：

- `local_time`
- `clock_rate`
- `offset_estimate`
- `initialized`

同步策略如下：

- 启动阶段阻塞调用 `pyntp`，直到成功获取参考时间
- 初始化完成后，仅通过内部推进更新设备时间
- 每隔 `sync_interval` 秒尝试获取新的参考时间
- 使用指数平滑更新 `offset_estimate`
- 根据偏移调整 `clock_rate`
- 将 `clock_rate` 限制在 `[0.9, 1.1]`
- 同步失败时仅输出 `warning`，不中断采样和发送

## 日志说明

设备端发送日志示例：

```text
sent packet timestamp=1775822528 samples=2 padded=6
```

字段含义：

- `samples`：本次真实采样条数
- `padded`：为凑满 8 条而补入的 `0xFFFF` 数量

## 当前默认配置

- 服务端时间误差默认值为 `30` 秒，便于本地联调
- 防重放缓存 TTL 默认与时间误差联动
- 清空数据库操作默认仅清空采集数据，不删除设备与主密钥
- 同一批次有效数据在数据库中按时间升序保存

如果需要更严格贴近题面，可使用：

```powershell
pixi run server --max-time-skew 5 --replay-ttl 10
```

## 已验证内容

- `device/` 与 `server/` 模块可以正常编译
- 数据库可以创建、查询和更新设备信息
- 服务端可动态读取数据库中的主密钥处理 UDP 报文
- 设备端报文可被服务端正确解析、解密并入库
- 图形界面所依赖的数据层和服务端主流程已联通
