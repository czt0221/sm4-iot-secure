# sm4-iot-secure

English | [简体中文](./README.md)

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![Pixi](https://img.shields.io/badge/Env-pixi-6D28D9)
![Crypto](https://img.shields.io/badge/Crypto-SM4--GCM%20%2B%20HMAC--SM3-0F766E)
![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)
![GUI](https://img.shields.io/badge/GUI-tkinter%20%2B%20tkcalendar-1F2937)

`sm4-iot-secure` is a Python-based IoT secure communication demo focused on secure transmission of temperature data. It includes an encrypted device-side sender, UDP communication, gradual time synchronization, and a server-side receiver with validation, decryption, database storage, and a graphical management interface.

## Features

- The device generates one temperature sample per device second
- A FIFO buffer of length 8 stores the most recent samples
- One fixed-length UDP packet is sent whenever `timestamp % 8 == 0`
- `HMAC-SM3` is used to derive an hourly `SM4` session key
- `SM4-GCM` is used to encrypt and authenticate 8 encoded temperature values
- The server stores received data in a local `SQLite` database
- The server dynamically looks up device IDs and master keys from the database for every UDP packet
- The server provides a GUI for data filtering, device management, and SQL execution

## Tech Stack

- `Python 3.14`
- `pixi`
- `cryptography`
- `pyntp`
- `tkinter`
- `tkcalendar`
- `SQLite`

## Quick Start

### Requirements

- `Windows`
- `pixi`
- Access to `pool.ntp.org`

### Install Dependencies

```powershell
pixi install
```

### Start the Server GUI

```powershell
pixi run server
```

### Start the Device

```powershell
pixi run device
```

### Common Startup Arguments

Server:

```powershell
pixi run server --host 0.0.0.0 --port 9999 --max-time-skew 30
```

Headless server:

```powershell
pixi run server --headless
```

Device:

```powershell
pixi run device --host 127.0.0.1 --port 9999 --sync-interval 60
```

## Project Structure

### Repository Files

```text
sm4-iot-secure/
├── .gitattributes                  # Git attributes
├── .gitignore                      # Git ignore rules
├── pixi.toml                       # pixi environment, dependencies, and tasks
├── pixi.lock                       # pixi lock file
├── README.md                       # Chinese documentation
├── README-en.md                    # English documentation
├── device/                         # Device-side code
│   ├── __init__.py                 # Package marker
│   ├── main.py                     # Device entry point: sampling, buffering, encryption, sending
│   ├── encryptor/                  # Device encryption and credential directory
│   │   ├── __init__.py             # Package marker
│   │   ├── encryptor.py            # Encryption entry and hourly key cache
│   │   ├── generate_key.bat        # Generate device id and master_key
│   │   ├── hmac_sm3.py             # HMAC-SM3 hourly key derivation
│   │   ├── random.py               # IV generation
│   │   └── sm4_gcm.py              # SM4-GCM encryption
│   ├── network/                    # Networking and time synchronization
│   │   ├── __init__.py             # Package marker
│   │   ├── network.py              # Network module entry
│   │   ├── send.py                 # UDP sending logic
│   │   ├── time.py                 # Gradual clock synchronization and device clock
│   │   └── udp.py                  # UDP packet construction
│   └── sensor/                     # Temperature sampling and encoding
│       ├── __init__.py             # Package marker
│       ├── fake.py                 # Deterministic fake temperature generator
│       ├── float_to_byte.py        # Encode temperature float into uint16
│       └── sensor.py               # Sensor entry
└── server/                         # Server-side code
    ├── __init__.py                 # Package marker
    ├── byte_to_float.py            # Decode uint16 temperature values
    ├── cache.py                    # Replay protection cache
    ├── database.py                 # SQLite access layer
    ├── gui.py                      # Graphical management interface
    ├── hmac_sm3.py                 # HMAC-SM3 hourly key derivation
    ├── main.py                     # Server entry point
    ├── receive.py                  # UDP receive, validation, decryption, and storage flow
    ├── sm4_gcm.py                  # SM4-GCM decryption
    └── udp.py                      # UDP packet parsing
```

### Files Generated at Runtime

- `device/encryptor/id`
  - Device ID file
- `device/encryptor/master_key`
  - Device master key file
- `server/server.db`
  - SQLite database file
- `server/server.db-shm`
  - SQLite shared memory file
- `server/server.db-wal`
  - SQLite WAL file
- `server/gui_state.json`
  - Saved GUI filter and sort state

## Database Storage

The server stores device information and measurements in a local single-file `SQLite` database:

```text
server/server.db
```

The database contains two core tables:

- `devices`
  - Stores device ID, master key, note, and creation time
- `measurements`
  - Stores device ID, timestamp, temperature value, and insertion time

Timestamps are stored as raw Unix timestamps in the database and converted into formatted date-time text in the GUI.

## Runtime Arguments

### Server Arguments

- `--host`: UDP bind address
- `--port`: UDP bind port
- `--server-dir`: server working directory, default `server/`
- `--max-time-skew`: allowed timestamp skew in seconds, default `30`
- `--replay-ttl`: replay cache TTL in seconds, default `max(10, 2 * max-time-skew)`
- `--log-level`: logging level
- `--headless`: run without launching the GUI

### Device Arguments

- `--host`: server address
- `--port`: server UDP port
- `--sync-interval`: time synchronization interval, default `60`
- `--device-dir`: device credential directory, default `device/encryptor/`
- `--log-level`: logging level

## Server GUI

### Data Management

- Filter by device
- Filter by time range
- Use a calendar widget for the date and hour/minute/second inputs for time
- Sort by timestamp or value
- Auto-refresh when filters change
- Manually refresh for newly received data under the same filters
- Remember device filter and sort state between launches
- Clear all stored measurement data

Displayed columns:

- Device ID
- Note
- Formatted datetime
- Raw timestamp
- Temperature value

### Device Management

- Allocate a new device ID and master key
- View all registered devices
- Edit notes in a popup dialog
- Delete a device and its associated measurements
- Write the selected device's `id` and `master_key` into a device directory
- Import `id` and `master_key` from a device directory into the database

### SQL Console

- Enter multi-line SQL
- Execute SQL statements
- Clear current SQL input
- View query results, affected row counts, and errors in the log area

Example SQL:

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
SET note = 'Lab Device 1'
WHERE id = 1;
```

```sql
DELETE FROM measurements
WHERE device_id = 1;
```

## Device Credentials and Allocation

The device requires these two files:

- `device/encryptor/id`
- `device/encryptor/master_key`

There are two ways to generate device credentials.

### Option 1: Use the Server GUI

1. Click `分配新设备` in the device management tab
2. Enter a note, or leave it empty
3. The server generates a new device ID and a 16-byte master key
4. If needed, select the device and click `写入设备目录`

The server also supports reverse import:

1. Click `从设备目录导入`
2. Select a `device` directory or a `device/encryptor` directory
3. The server reads `id` and `master_key`
4. If the device ID already exists, the import is rejected

### Option 2: Generate Credentials in the Device Directory

Run:

```powershell
device\encryptor\generate_key.bat
```

This writes:

- `id`
- `master_key`

into `device/encryptor/`.

If the server should recognize this device, import the credentials through the GUI afterward.

## Protocol

### Temperature Encoding

- Type: `uint16`
- Byte order: `big-endian`
- Encoding formula:

```text
encoded = int((value + 99.9) * 10)
```

- Valid range:
  - `0x0000 -> -99.9`
  - `0x07CE -> 99.9`
- `0xFFFF` means `padding`

### Timestamp

- Type: `uint32`
- Unit: seconds
- Source: device-side monotonic business time

### Plaintext Layout

- Total length: 16 bytes
- Contains 8 encoded temperature values, 2 bytes each

### AAD

- Total length: 8 bytes
- Layout: `id(4B) + timestamp(4B)`
- Byte order: `big-endian`

### UDP Packet Layout

```text
[0:4]   timestamp   uint32
[4:8]   id          uint32
[8:24]  ciphertext  16B
[24:36] tag         12B
[36:48] iv          12B
```

Total packet length is fixed at 48 bytes.

## Keys and Encryption

The device and server derive the hourly key as follows:

```text
hour_index = timestamp // 3600
hour_key = HMAC-SM3(master_key, hour_index)
```

The first 16 bytes of the `HMAC-SM3` output are used as the `SM4` key.

Encryption parameters:

- Algorithm: `SM4-GCM`
- IV length: 12 bytes
- Tag length: 12 bytes
- All random values use `os.urandom`

## Time Synchronization

The device maintains its own local business clock instead of directly using system time. The main state variables are:

- `local_time`
- `clock_rate`
- `offset_estimate`
- `initialized`

Synchronization strategy:

- At startup, block until `pyntp` successfully returns a reference time
- After initialization, advance device time only through the internal clock model
- Attempt synchronization every `sync_interval` seconds
- Update `offset_estimate` using exponential smoothing
- Adjust `clock_rate` according to the estimated offset
- Clamp `clock_rate` to `[0.9, 1.1]`
- On synchronization failure, log a warning but continue sampling and sending

## Fake Temperature Generation

`device/sensor/fake.py` uses a deterministic temperature function with inputs `device_id` and `timestamp`. Therefore, the same device at the same timestamp always produces the same value.

The generated value combines:

- Annual cycle
  - Simulates the four seasons in North China
- Daily cycle
  - Simulates warmer daytime and cooler nighttime temperatures
- Device-specific constant offset
  - Gives each device a stable but small difference
- Low-frequency special disturbance
  - Simulates slow environmental variation without using weather data
- Short-period micro disturbance
  - Prevents short windows from becoming completely flat

Current properties:

- Output keeps one decimal place
- One sample is generated per second
- The temperature difference between adjacent seconds is kept within `0.2`
- Temperature is clamped to `-20.0 ~ 42.0`

## Server Checks Before Storage

Before storing a UDP packet, the server performs the following steps:

1. Parse the packet according to the fixed 48-byte protocol
2. Validate that the timestamp is within the allowed skew window and satisfies `timestamp % 8 == 0`
3. Check replay protection cache for `(device_id, timestamp)`
4. Dynamically look up the device master key from the database
5. Derive the hourly session key and run `SM4-GCM` decryption and authentication
6. Parse the 8 encoded temperature values
7. Filter `0xFFFF` padding and restore an individual timestamp for each valid value
8. Check whether any adjacent 1-second temperature difference exceeds `0.2`
9. Store the values and update the replay cache

Temperature encoding rules on the server:

- `0x0000 ~ 0x07CE` are valid temperature encodings
- `0xFFFF` is padding
- Any other encoding is treated as invalid and causes the whole packet to be rejected

Adjacent-second temperature difference checks:

- Only truly adjacent seconds are compared
- For the earliest valid value in the current packet, the server also checks the previous second from the database
- If the previous second does not exist, that comparison is skipped
- If the absolute difference is greater than `0.2`, only a warning is logged; the packet is still stored

## Logs

Example device send log:

```text
sent packet timestamp=1775822528 samples=2 padded=6
```

Field meaning:

- `samples`: number of real samples in this packet
- `padded`: number of `0xFFFF` values added to reach 8 slots

Common server log examples:

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

## Default Configuration

- Default server timestamp tolerance is `30` seconds for easier local testing
- Replay cache TTL is linked to the timestamp tolerance by default
- Clearing data removes only measurements, not device credentials
- Valid measurements from the same packet are stored in ascending timestamp order

For a stricter configuration:

```powershell
pixi run server --max-time-skew 5 --replay-ttl 10
```

## Translation

This document is translated from the original Chinese [README.md](./README.md) with the assistance of ChatGPT.
