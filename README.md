<div align="center">

# sm4-iot-secure

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Pixi](https://img.shields.io/badge/Env-pixi-6D28D9)
![Crypto](https://img.shields.io/badge/Crypto-SM4--GCM%20%2B%20HMAC--SM3-0F766E)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-tkinter%20%2B%20tkcalendar-1F2937)
[![Release](https://img.shields.io/github/v/release/czt0221/sm4-iot-secure)](https://github.com/czt0221/sm4-iot-secure/releases/latest)

[![Download](https://img.shields.io/badge/Download-Latest%20Release-2ea44f?style=for-the-badge)](https://github.com/czt0221/sm4-iot-secure/releases/latest)

[English](./README-en.md) | 简体中文

</div>

`sm4-iot-secure` 是一个基于 Python 的物联网安全通信示例项目，围绕温度数据的安全传输实现设备端加密发送、UDP 通信、渐进式时间同步，以及服务端验包、解密、入库和图形化管理。

## 功能概览

- 设备端每生成 1 个设备秒，采集 1 条温度数据
- 使用长度为 8 的 FIFO 缓存保存最近采样值
- 当 `timestamp % 8 == 0` 时发送 1 个固定长度 UDP 报文
- 使用 `HMAC-SM3` 按小时派生 `SM4` 会话密钥
- 使用 `SM4-GCM` 对 8 个温度编码值进行认证加密
- 服务端收到数据后写入本地 `SQLite` 数据库
- 服务端每次收到 UDP 报文都会动态查询数据库中的设备 ID 和主密钥
- 服务端提供图形界面，支持数据筛选、设备管理和 SQL 控制台

## 技术栈

- `Python 3.14`
- `pixi`
- `cryptography`
- `pyntp`
- `tkinter`
- `tkcalendar`
- `SQLite`

## 快速启动

### 环境要求

- `Windows`
- 已安装 `pixi`
- 可访问 `pool.ntp.org`

### 安装依赖

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

### 打包环境

项目额外提供一个 `build` 环境，用于放置 `PyInstaller` 这类构建工具，而不污染默认运行环境。

安装 `build` 环境：

```powershell
pixi install -e build
```

执行打包：

```powershell
pixi run -e build build-server
pixi run -e build build-device
```

## 项目结构

### 仓库文件

```text
sm4-iot-secure/
├── .gitattributes                  # Git 属性配置
├── .gitignore                      # Git 忽略规则
├── pixi.toml                       # pixi 环境、依赖和任务定义
├── pixi.lock                       # pixi 锁文件
├── README.md                       # 项目说明文档
├── README-en.md                    # 英文说明文档
├── server.spec                     # 服务端 PyInstaller 打包配置
├── device.spec                     # 设备端 PyInstaller 打包配置
├── device/                         # 设备端代码
│   ├── __init__.py                 # 设备端包标记
│   ├── main.py                     # 设备端主入口，负责采样、缓存、加密、发送
│   ├── encryptor/                  # 设备端加密与凭据目录
│   │   ├── __init__.py             # 加密子包标记
│   │   ├── encryptor.py            # 加密入口与小时密钥缓存
│   │   ├── generate_key.bat        # 为 device 生成 id 和 master_key 的脚本
│   │   ├── hmac_sm3.py             # HMAC-SM3 小时密钥派生
│   │   ├── random.py               # IV 生成
│   │   └── sm4_gcm.py              # SM4-GCM 加密实现
│   ├── network/                    # 网络通信与时间同步
│   │   ├── __init__.py             # 网络子包标记
│   │   ├── network.py              # 网络模块入口
│   │   ├── send.py                 # UDP 发送逻辑
│   │   ├── time.py                 # 渐进式时间同步与设备时钟
│   │   └── udp.py                  # UDP 报文封装
│   └── sensor/                     # 温度采样与编码
│       ├── __init__.py             # 传感器子包标记
│       ├── fake.py                 # 模拟温度数据生成
│       ├── float_to_byte.py        # 温度浮点值编码为 uint16
│       └── sensor.py               # 传感器统一入口
└── server/                         # 服务端代码
    ├── __init__.py                 # 服务端包标记
    ├── byte_to_float.py            # uint16 温度值解码
    ├── cache.py                    # 防重放缓存
    ├── database.py                 # SQLite 数据库访问封装
    ├── gui.py                      # 图形化管理界面
    ├── hmac_sm3.py                 # HMAC-SM3 小时密钥派生
    ├── main.py                     # 服务端主入口
    ├── receive.py                  # UDP 接收、验包、解密、入库流程
    ├── sm4_gcm.py                  # SM4-GCM 解密实现
    └── udp.py                      # UDP 报文解析
```

### 运行后生成的文件

- `device/encryptor/id`
  - 设备 ID 配置文件
- `device/encryptor/master_key`
  - 设备主密钥配置文件
- `server/server.db`
  - SQLite 数据库主文件
- `server/server.db-shm`
  - SQLite 共享内存文件
- `server/server.db-wal`
  - SQLite WAL 日志文件
- `server/gui_state.json`
  - GUI 保存的上次设备筛选与排序状态
- `build/`
  - PyInstaller 构建中间文件目录
- `dist/`
  - PyInstaller 最终打包输出目录

## 数据库存储

服务端使用本地单文件 `SQLite` 数据库存储设备信息与测量数据：

```text
server/server.db
```

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

### 数据管理

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

### 设备管理

- 分配新的设备 ID 与主密钥
- 查看所有已分配设备
- 通过弹窗修改设备备注
- 删除设备及其关联采集数据
- 将选中设备的 `id` 和 `master_key` 写入目标设备目录
- 从目标设备目录读取 `id` 和 `master_key` 并导入数据库

设备目录导入导出同时兼容两种布局：

- 源码运行目录
  - `device/encryptor/id`
  - `device/encryptor/master_key`
- PyInstaller 打包后的设备发布目录
  - `device/_internal/encryptor/id`
  - `device/_internal/encryptor/master_key`

### SQL 控制台

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

设备端运行依赖以下两个文件：

- `device/encryptor/id`
- `device/encryptor/master_key`

生成设备凭据有两种方式：

### 方式一：使用服务端图形界面

1. 在“设备管理”中点击“分配新设备”
2. 输入备注，可留空
3. 服务端自动生成设备 ID 和 16 字节主密钥
4. 如需写入设备目录，选中设备后点击“写入设备目录”

服务端也支持反向导入：

1. 在“设备管理”中点击“从设备目录导入”
2. 选择 `device` 目录或 `device/encryptor` 目录
3. 服务端读取其中的 `id` 和 `master_key`
4. 若设备 ID 已存在，则拒绝导入并提示错误

### 方式二：在设备目录生成凭据

运行以下脚本：

```powershell
device\encryptor\generate_key.bat
```

脚本会直接在 `device/encryptor/` 下生成：

- `id`
- `master_key`

如果需要让服务端识别该设备，可再通过图形界面的“从设备目录导入”将其写入数据库。

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
  - `0x07CE -> 99.9`
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

## 模拟温度生成

`device/sensor/fake.py` 使用确定性温度函数生成模拟数据，输入为 `device_id` 和 `timestamp`，因此同一设备在同一时间戳下总会得到相同温度。

生成模型由以下几部分叠加组成：

- 年周期
  - 模拟华北地区四季变化
- 日周期
  - 模拟昼夜温差，白天偏高、夜间偏低
- 设备固定偏移
  - 不同设备在同一时刻会有稳定但较小的差异
- 低频特殊扰动
  - 模拟不依赖天气的环境缓慢变化
- 短周期微扰
  - 让短时间窗口内的数据不会长期完全不变

当前实现特性：

- 输出保留 1 位小数
- 每秒生成 1 条数据
- 相邻 1 秒的温差控制在 `0.2` 以内
- 温度范围限制为 `-20.0 ~ 42.0`

## 服务端入库前检查

服务端在把一条 UDP 报文写入数据库前，会依次进行以下处理：

1. 按固定 48 字节协议解析报文
2. 校验时间戳必须落在允许误差窗口内，且满足 `timestamp % 8 == 0`
3. 检查 `(device_id, timestamp)` 是否命中防重放缓存
4. 动态查询数据库中的设备主密钥
5. 按小时派生会话密钥，执行 `SM4-GCM` 解密和认证
6. 解析 8 个温度编码值
7. 过滤 `0xFFFF` padding，并还原每个有效数据自己的时间戳
8. 检查相邻 1 秒温差是否超过 `0.2`
9. 入库并更新防重放缓存

其中温度编码规则如下：

- `0x0000 ~ 0x07CE` 为合法温度编码
- `0xFFFF` 为 padding
- 其他编码一律视为非法，整包拒绝

相邻秒温差检查规则如下：

- 只比较真正相邻 1 秒的数据
- 对当前包中最早的有效数据，会额外查询数据库中的前一秒记录
- 如果前一秒不存在，则跳过这组比较
- 如果温差绝对值大于 `0.2`，只记录 `warning`，不拒绝入库

## 日志说明

设备端发送日志示例：

```text
sent packet timestamp=1775822528 samples=2 padded=6
```

字段含义：

- `samples`：本次真实采样条数
- `padded`：为凑满 8 条而补入的 `0xFFFF` 数量

服务端常见日志示例：

```text
stored 8 measurements from device=1 timestamp=1775822528
```

```text
failed to handle packet from ('127.0.0.1', 54321): replay packet detected
```

```text
failed to handle packet from ('127.0.0.1', 54321): invalid temperature encoding: 0x07CF
```

```text
temperature jump detected for device=1 between timestamp=1775822520 and timestamp=1775822521: 21.0 -> 21.4
```

## 当前默认配置

- 服务端时间误差默认值为 `30` 秒，便于本地联调
- 防重放缓存 TTL 默认与时间误差联动
- 清空数据库操作默认仅清空采集数据，不删除设备与主密钥
- 同一批次有效数据在数据库中按时间升序保存

如需更严格的时间误差限制，可使用：

```powershell
pixi run server --max-time-skew 5 --replay-ttl 10
```
