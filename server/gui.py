from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from datetime import date, datetime, time as dt_time
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from tkcalendar import DateEntry

from server.database import DeviceRecord, MeasurementRecord, ServerDatabase
from server.receive import UDPServer

STATE_FILE_NAME = "gui_state.json"
ALL_DEVICES_LABEL = "全部设备"


def _parse_date_value(value: str) -> date:
    return date.fromisoformat(value)


class ServerGUI:
    def __init__(
        self,
        host: str,
        port: int,
        server_dir: Path,
        max_time_skew: int,
        replay_ttl: int | None,
    ) -> None:
        self.server_dir = server_dir
        self.database = ServerDatabase(server_dir / "server.db")
        self.state_path = server_dir / STATE_FILE_NAME
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._refresh_job: str | None = None
        self._suspend_auto_refresh = False
        self._pending_focus_job: str | None = None
        self._time_input_widgets: set[tk.Widget] = set()

        self.server = UDPServer(
            host=host,
            port=port,
            database=self.database,
            max_time_skew=max_time_skew,
            replay_ttl=replay_ttl,
            event_callback=self._queue_log,
        )
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)

        state = self._load_state()

        self.root = tk.Tk()
        self.root.title("SM4 IoT Secure Server")
        self.root.geometry("1240x780")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Return>", self._on_commit_time_input, add="+")
        self.root.bind("<Button-1>", self._on_root_click, add="+")

        self.device_filter_var = tk.StringVar(value=state.get("device_filter", ALL_DEVICES_LABEL))
        self.sort_field_var = tk.StringVar(value=state.get("sort_field", "timestamp"))
        self.sort_order_var = tk.StringVar(value=state.get("sort_order", "DESC"))

        today_text = date.today().isoformat()
        self.start_date_var = tk.StringVar(value=today_text)
        self.start_hour_var = tk.StringVar(value="00")
        self.start_minute_var = tk.StringVar(value="00")
        self.start_second_var = tk.StringVar(value="00")
        self.start_enabled_var = tk.BooleanVar(value=False)

        self.end_date_var = tk.StringVar(value=today_text)
        self.end_hour_var = tk.StringVar(value="23")
        self.end_minute_var = tk.StringVar(value="59")
        self.end_second_var = tk.StringVar(value="59")
        self.end_enabled_var = tk.BooleanVar(value=False)

        self.selected_device_id: int | None = None
        self._last_valid_time_state = self._capture_time_state()

        self._build_layout(host, port, max_time_skew, replay_ttl)
        self._bind_auto_refresh()
        self.server_thread.start()
        self.refresh_devices()
        self.refresh_measurements()
        self.root.after(300, self._drain_logs)

    def _load_state(self) -> dict[str, object]:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_state(self) -> None:
        state = {
            "device_filter": self.device_filter_var.get(),
            "sort_field": self.sort_field_var.get(),
            "sort_order": self.sort_order_var.get(),
        }
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _capture_time_state(self) -> dict[str, object]:
        return {
            "start_enabled": self.start_enabled_var.get(),
            "start_date": self.start_date_var.get(),
            "start_hour": self.start_hour_var.get(),
            "start_minute": self.start_minute_var.get(),
            "start_second": self.start_second_var.get(),
            "end_enabled": self.end_enabled_var.get(),
            "end_date": self.end_date_var.get(),
            "end_hour": self.end_hour_var.get(),
            "end_minute": self.end_minute_var.get(),
            "end_second": self.end_second_var.get(),
        }

    def _restore_time_state(self, state: dict[str, object]) -> None:
        self._suspend_auto_refresh = True
        self.start_enabled_var.set(bool(state["start_enabled"]))
        self.start_date_var.set(str(state["start_date"]))
        self.start_hour_var.set(str(state["start_hour"]))
        self.start_minute_var.set(str(state["start_minute"]))
        self.start_second_var.set(str(state["start_second"]))
        self.end_enabled_var.set(bool(state["end_enabled"]))
        self.end_date_var.set(str(state["end_date"]))
        self.end_hour_var.set(str(state["end_hour"]))
        self.end_minute_var.set(str(state["end_minute"]))
        self.end_second_var.set(str(state["end_second"]))
        self._suspend_auto_refresh = False

    def _build_layout(self, host: str, port: int, max_time_skew: int, replay_ttl: int | None) -> None:
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text=(
                f"监听地址: {host}:{port}    "
                f"时间误差: {max_time_skew}s    "
                f"防重放TTL: {replay_ttl or max(10, max_time_skew * 2)}s"
            ),
        ).pack(anchor=tk.W)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        data_tab = ttk.Frame(notebook, padding=10)
        device_tab = ttk.Frame(notebook, padding=10)
        sql_tab = ttk.Frame(notebook, padding=10)
        notebook.add(data_tab, text="数据管理")
        notebook.add(device_tab, text="设备管理")
        notebook.add(sql_tab, text="SQL 控制台")

        self._build_data_tab(data_tab)
        self._build_device_tab(device_tab)
        self._build_sql_tab(sql_tab)

        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _build_data_tab(self, parent: ttk.Frame) -> None:
        filter_frame = ttk.LabelFrame(parent, text="筛选条件", padding=10)
        filter_frame.pack(fill=tk.X)

        ttk.Label(filter_frame, text="设备").grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.device_filter_box = ttk.Combobox(
            filter_frame,
            textvariable=self.device_filter_var,
            state="readonly",
            width=24,
        )
        self.device_filter_box.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)

        self._build_time_filter_row(
            parent=filter_frame,
            row=0,
            start_column=2,
            label="开始时间",
            enabled_var=self.start_enabled_var,
            date_var=self.start_date_var,
            hour_var=self.start_hour_var,
            minute_var=self.start_minute_var,
            second_var=self.start_second_var,
            default_time=("00", "00", "00"),
        )

        self._build_time_filter_row(
            parent=filter_frame,
            row=1,
            start_column=2,
            label="结束时间",
            enabled_var=self.end_enabled_var,
            date_var=self.end_date_var,
            hour_var=self.end_hour_var,
            minute_var=self.end_minute_var,
            second_var=self.end_second_var,
            default_time=("23", "59", "59"),
        )

        ttk.Label(filter_frame, text="排序字段").grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Combobox(
            filter_frame,
            textvariable=self.sort_field_var,
            values=("timestamp", "value"),
            state="readonly",
            width=18,
        ).grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Label(filter_frame, text="排序方向").grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Combobox(
            filter_frame,
            textvariable=self.sort_order_var,
            values=("ASC", "DESC"),
            state="readonly",
            width=18,
        ).grid(row=2, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Button(filter_frame, text="刷新", command=self.refresh_measurements).grid(
            row=2,
            column=2,
            sticky=tk.W,
            padx=4,
            pady=4,
        )
        ttk.Button(filter_frame, text="清空数据", command=self.clear_measurements).grid(
            row=2,
            column=3,
            sticky=tk.W,
            padx=4,
            pady=4,
        )

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        columns = ("device_id", "note", "datetime", "timestamp", "value")
        self.measurement_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for column, title, width in (
            ("device_id", "设备ID", 90),
            ("note", "备注", 180),
            ("datetime", "时间", 180),
            ("timestamp", "时间戳", 120),
            ("value", "温度值", 100),
        ):
            self.measurement_tree.heading(column, text=title)
            self.measurement_tree.column(column, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.measurement_tree.yview)
        self.measurement_tree.configure(yscrollcommand=scrollbar.set)
        self.measurement_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_time_filter_row(
        self,
        parent: ttk.LabelFrame,
        row: int,
        start_column: int,
        label: str,
        enabled_var: tk.BooleanVar,
        date_var: tk.StringVar,
        hour_var: tk.StringVar,
        minute_var: tk.StringVar,
        second_var: tk.StringVar,
        default_time: tuple[str, str, str],
    ) -> None:
        ttk.Checkbutton(parent, text=label, variable=enabled_var).grid(
            row=row,
            column=start_column,
            sticky=tk.W,
            padx=4,
            pady=4,
        )

        date_entry = DateEntry(
            parent,
            textvariable=date_var,
            date_pattern="yyyy-mm-dd",
            width=12,
            locale="zh_CN",
        )
        date_entry.grid(row=row, column=start_column + 1, sticky=tk.W, padx=4, pady=4)

        hour_box = ttk.Combobox(
            parent,
            textvariable=hour_var,
            values=[f"{value:02d}" for value in range(24)],
            width=4,
        )
        minute_box = ttk.Combobox(
            parent,
            textvariable=minute_var,
            values=[f"{value:02d}" for value in range(60)],
            width=4,
        )
        second_box = ttk.Combobox(
            parent,
            textvariable=second_var,
            values=[f"{value:02d}" for value in range(60)],
            width=4,
        )

        if not hour_var.get():
            hour_var.set(default_time[0])
        if not minute_var.get():
            minute_var.set(default_time[1])
        if not second_var.get():
            second_var.set(default_time[2])

        hour_box.grid(row=row, column=start_column + 2, sticky=tk.W, padx=(4, 0), pady=4)
        ttk.Label(parent, text=":").grid(row=row, column=start_column + 3, sticky=tk.W)
        minute_box.grid(row=row, column=start_column + 4, sticky=tk.W, pady=4)
        ttk.Label(parent, text=":").grid(row=row, column=start_column + 5, sticky=tk.W)
        second_box.grid(row=row, column=start_column + 6, sticky=tk.W, padx=(0, 4), pady=4)

        self._time_input_widgets.update({date_entry, hour_box, minute_box, second_box})

        self._set_entry_validation(date_entry, allowed_chars="0123456789-")
        self._set_combobox_validation(hour_box, allowed_chars="0123456789:")
        self._set_combobox_validation(minute_box, allowed_chars="0123456789:")
        self._set_combobox_validation(second_box, allowed_chars="0123456789:")

        self._bind_date_formatting(date_entry)
        self._bind_date_autojump(date_entry, hour_box)
        self._bind_time_autojump(hour_box, minute_box, 23)
        self._bind_time_autojump(minute_box, second_box, 59)
        self._bind_time_autojump(second_box, None, 59)
        self._bind_validation_on_selection(date_entry)
        self._bind_validation_on_selection(hour_box)
        self._bind_validation_on_selection(minute_box)
        self._bind_validation_on_selection(second_box)
        self._bind_validation_on_focus_out(date_entry)
        self._bind_validation_on_focus_out(hour_box)
        self._bind_validation_on_focus_out(minute_box)
        self._bind_validation_on_focus_out(second_box)

    def _bind_date_formatting(self, widget: DateEntry) -> None:
        def on_key_release(_event: tk.Event) -> None:
            raw = widget.get()
            digits = "".join(ch for ch in raw if ch.isdigit())[:8]
            if not digits:
                return

            parts: list[str] = []
            if len(digits) <= 4:
                parts.append(digits)
            elif len(digits) <= 6:
                parts.append(digits[:4])
                parts.append(digits[4:])
            else:
                parts.append(digits[:4])
                parts.append(digits[4:6])
                parts.append(digits[6:])
            formatted = "-".join(parts)
            if not formatted:
                return
            if formatted != raw:
                cursor = len(formatted)
                widget.delete(0, tk.END)
                widget.insert(0, formatted)
                widget.icursor(cursor)

            if len(digits) == 8:
                try:
                    _parse_date_value(formatted)
                except ValueError:
                    self._restore_time_state(self._last_valid_time_state)
                    messagebox.showwarning("日期输入无效", "请输入有效日期，格式为 YYYY-MM-DD。")

        widget.bind("<KeyRelease>", on_key_release, add="+")

    def _bind_date_autojump(self, current_widget: DateEntry, next_widget: ttk.Combobox) -> None:
        def on_key_release(event: tk.Event) -> None:
            text = current_widget.get().strip()
            if len(text) != 10:
                return
            try:
                _parse_date_value(text)
            except ValueError:
                return
            self._focus_widget(next_widget)

        current_widget.bind("<KeyRelease>", on_key_release, add="+")

    def _set_entry_validation(self, widget: tk.Widget, allowed_chars: str) -> None:
        command = self.root.register(lambda proposed: all(ch in allowed_chars for ch in proposed))
        widget.configure(validate="key", validatecommand=(command, "%P"))

    def _set_combobox_validation(self, widget: ttk.Combobox, allowed_chars: str) -> None:
        command = self.root.register(lambda proposed: all(ch in allowed_chars for ch in proposed))
        widget.configure(validate="key", validatecommand=(command, "%P"))

    def _bind_validation_on_focus_out(self, widget: tk.Widget) -> None:
        widget.bind("<FocusOut>", self._on_time_input_focus_out, add="+")

    def _bind_validation_on_selection(self, widget: tk.Widget) -> None:
        widget.bind("<<ComboboxSelected>>", self._on_time_input_selection, add="+")
        widget.bind("<<DateEntrySelected>>", self._on_time_input_selection, add="+")

    def _bind_time_autojump(
        self,
        current_widget: ttk.Combobox,
        next_widget: ttk.Combobox | None,
        max_value: int,
    ) -> None:
        def on_key_release(event: tk.Event) -> None:
            text = current_widget.get().strip()
            if not text:
                return

            if text.endswith(":"):
                text = text[:-1]
                current_widget.delete(0, tk.END)
                current_widget.insert(0, text)
                if self._is_valid_time_part(text, max_value):
                    self._focus_widget(next_widget)
                return

            if len(text) < 2:
                return

            if self._is_valid_time_part(text[:2], max_value):
                current_widget.delete(0, tk.END)
                current_widget.insert(0, text[:2])
                self._defer_focus_widget(next_widget)
                if next_widget is None:
                    self.root.after_idle(self.measurement_tree.focus_set)

        current_widget.bind("<KeyRelease>", on_key_release, add="+")

    def _is_valid_time_part(self, value: str, max_value: int) -> bool:
        if len(value) != 2 or not value.isdigit():
            return False
        return 0 <= int(value) <= max_value

    def _focus_widget(self, widget: ttk.Combobox | None) -> None:
        if widget is None:
            return
        widget.focus_set()
        widget.selection_range(0, tk.END)

    def _defer_focus_widget(self, widget: ttk.Combobox | None) -> None:
        if widget is None:
            return
        if self._pending_focus_job is not None:
            self.root.after_cancel(self._pending_focus_job)
        self._pending_focus_job = self.root.after(80, lambda: self._finish_deferred_focus(widget))

    def _finish_deferred_focus(self, widget: ttk.Combobox) -> None:
        self._pending_focus_job = None
        self._focus_widget(widget)

    def _build_device_tab(self, parent: ttk.Frame) -> None:
        top = ttk.Frame(parent)
        top.pack(fill=tk.X)
        ttk.Button(top, text="分配新设备", command=self.create_device).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(top, text="修改备注", command=self.update_selected_note).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(top, text="删除设备", command=self.delete_selected_device).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(top, text="刷新设备列表", command=self.refresh_devices).pack(side=tk.LEFT)
        ttk.Button(top, text="写入设备目录", command=self.export_selected_device).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="从设备目录导入", command=self.import_device_from_directory).pack(side=tk.LEFT, padx=(8, 0))

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        columns = ("device_id", "note", "master_key", "created_at")
        self.device_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for column, title, width in (
            ("device_id", "设备ID", 90),
            ("note", "备注", 180),
            ("master_key", "主密钥", 320),
            ("created_at", "创建时间", 180),
        ):
            self.device_tree.heading(column, text=title)
            self.device_tree.column(column, width=width, anchor=tk.CENTER)
        self.device_tree.bind("<<TreeviewSelect>>", self._on_device_selected)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=scrollbar.set)
        self.device_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_sql_tab(self, parent: ttk.Frame) -> None:
        action_bar = ttk.Frame(parent)
        action_bar.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(action_bar, text="执行 SQL", command=self.execute_sql_from_editor).pack(side=tk.LEFT)
        ttk.Button(action_bar, text="清空输入", command=self.clear_sql_editor).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(
            parent,
            text="可输入多行 SQL，执行结果会显示在下方日志区。建议每次执行一条完整语句。",
        ).pack(anchor=tk.W, pady=(0, 8))

        editor_frame = ttk.Frame(parent)
        editor_frame.pack(fill=tk.BOTH, expand=True)
        self.sql_text = tk.Text(editor_frame, height=16, wrap=tk.WORD)
        sql_scrollbar = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL, command=self.sql_text.yview)
        self.sql_text.configure(yscrollcommand=sql_scrollbar.set)
        self.sql_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sql_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _bind_auto_refresh(self) -> None:
        watched_vars: list[tk.Variable] = [
            self.device_filter_var,
            self.sort_field_var,
            self.sort_order_var,
            self.start_enabled_var,
            self.start_date_var,
            self.start_hour_var,
            self.start_minute_var,
            self.start_second_var,
            self.end_enabled_var,
            self.end_date_var,
            self.end_hour_var,
            self.end_minute_var,
            self.end_second_var,
        ]
        for variable in watched_vars:
            variable.trace_add("write", self._schedule_measurement_refresh)

    def _queue_log(self, level: str, message: str) -> None:
        self.log_queue.put((level.upper(), message))

    def _schedule_measurement_refresh(self, *_args: object) -> None:
        if self._suspend_auto_refresh:
            return
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
        self._refresh_job = self.root.after(300, self._run_scheduled_refresh)

    def _run_scheduled_refresh(self) -> None:
        self._refresh_job = None
        self.refresh_measurements(show_errors=False)

    def _append_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {level}: {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _format_sql_result(self, columns: list[str], rows: list[tuple[object, ...]], count: int) -> list[str]:
        if not columns:
            return [f"SQL执行完成，影响 {count} 行。"]

        lines = [f"SQL查询完成，返回 {count} 行。", " | ".join(columns)]
        preview_rows = rows[:20]
        for row in preview_rows:
            lines.append(" | ".join("" if value is None else str(value) for value in row))
        if count > len(preview_rows):
            lines.append(f"... 其余 {count - len(preview_rows)} 行未显示")
        return lines

    def _drain_logs(self) -> None:
        while not self.log_queue.empty():
            level, message = self.log_queue.get_nowait()
            self._append_log(level, message)
        self.root.after(300, self._drain_logs)

    def _device_filter_to_id(self) -> int | None:
        selection = self.device_filter_var.get()
        if selection == ALL_DEVICES_LABEL or not selection:
            return None
        return int(selection.split(" ", maxsplit=1)[0])

    def _build_full_timestamp(self, date_text: str, hour_text: str, minute_text: str, second_text: str) -> int:
        selected_date = _parse_date_value(date_text)
        selected_time = dt_time(
            hour=int(hour_text),
            minute=int(minute_text),
            second=int(second_text),
        )
        return int(datetime.combine(selected_date, selected_time).timestamp())

    def _validate_time_filters(self) -> tuple[int | None, int | None]:
        try:
            full_start_timestamp = self._build_full_timestamp(
                self.start_date_var.get(),
                self.start_hour_var.get(),
                self.start_minute_var.get(),
                self.start_second_var.get(),
            )
            full_end_timestamp = self._build_full_timestamp(
                self.end_date_var.get(),
                self.end_hour_var.get(),
                self.end_minute_var.get(),
                self.end_second_var.get(),
            )
        except ValueError:
            raise ValueError("请选择有效的日期和时间。") from None

        if full_start_timestamp > full_end_timestamp:
            raise ValueError("开始时间不能晚于结束时间。") from None

        start_timestamp = full_start_timestamp if self.start_enabled_var.get() else None
        end_timestamp = full_end_timestamp if self.end_enabled_var.get() else None
        return start_timestamp, end_timestamp

    def _on_time_input_focus_out(self, _event: tk.Event) -> None:
        if self._suspend_auto_refresh:
            return
        self.refresh_measurements(show_errors=True)

    def _on_time_input_selection(self, _event: tk.Event) -> None:
        if self._suspend_auto_refresh:
            return
        self.refresh_measurements(show_errors=True)

    def _on_commit_time_input(self, _event: tk.Event) -> str:
        self.measurement_tree.focus_set()
        self.refresh_measurements(show_errors=True)
        return "break"

    def _on_root_click(self, event: tk.Event) -> None:
        widget = event.widget
        if widget in self._time_input_widgets:
            return
        self.root.after_idle(self.measurement_tree.focus_set)

    def clear_sql_editor(self) -> None:
        self.sql_text.delete("1.0", tk.END)

    def execute_sql_from_editor(self) -> None:
        statement = self.sql_text.get("1.0", tk.END).strip()
        if not statement:
            messagebox.showwarning("SQL 为空", "请输入要执行的 SQL 语句。")
            return
        if statement.endswith(";"):
            statement = statement[:-1].strip()
        if not statement:
            return

        try:
            columns, rows, count = self.database.execute_sql(statement)
        except Exception as exc:
            self._append_log("ERROR", f"SQL执行失败: {exc}")
            messagebox.showerror("SQL 执行失败", str(exc))
            return

        self.refresh_devices()
        self.refresh_measurements(show_errors=False)
        for line in self._format_sql_result(columns, rows, count):
            self._append_log("INFO", line)

    def refresh_measurements(self, show_errors: bool = True) -> None:
        try:
            start_timestamp, end_timestamp = self._validate_time_filters()
        except ValueError as exc:
            if show_errors:
                self._restore_time_state(self._last_valid_time_state)
                messagebox.showwarning("时间输入无效", str(exc))
            return

        self._last_valid_time_state = self._capture_time_state()
        self._save_state()
        records = self.database.query_measurements(
            device_id=self._device_filter_to_id(),
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            sort_field=self.sort_field_var.get(),
            sort_desc=self.sort_order_var.get() == "DESC",
        )
        self._populate_measurements(records)

    def _populate_measurements(self, records: list[MeasurementRecord]) -> None:
        for item in self.measurement_tree.get_children():
            self.measurement_tree.delete(item)
        for record in records:
            self.measurement_tree.insert(
                "",
                tk.END,
                values=(
                    record.device_id,
                    record.note,
                    record.datetime_text,
                    record.timestamp,
                    record.value,
                ),
            )

    def refresh_devices(self) -> None:
        devices = self.database.list_devices()
        self._populate_devices(devices)
        values = [ALL_DEVICES_LABEL] + [
            f"{device.device_id} | {device.note}" if device.note else str(device.device_id) for device in devices
        ]
        self.device_filter_box["values"] = values

        current_filter = self.device_filter_var.get()
        if current_filter not in values:
            self._suspend_auto_refresh = True
            self.device_filter_var.set(ALL_DEVICES_LABEL)
            self._suspend_auto_refresh = False

    def _populate_devices(self, devices: list[DeviceRecord]) -> None:
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
        for device in devices:
            self.device_tree.insert(
                "",
                tk.END,
                iid=str(device.device_id),
                values=(device.device_id, device.note, device.master_key_hex, device.created_at),
            )

    def create_device(self) -> None:
        note = simpledialog.askstring(
            "分配新设备",
            "请输入设备备注，可留空：",
            parent=self.root,
        )
        if note is None:
            return
        record = self.database.create_device(note=note.strip())
        self.refresh_devices()
        self._append_log("INFO", f"已分配新设备: id={record.device_id}, key={record.master_key_hex}")
        messagebox.showinfo(
            "设备已分配",
            f"设备ID: {record.device_id}\n主密钥: {record.master_key_hex}\n备注: {record.note or '(空)'}",
        )

    def _on_device_selected(self, _event: object) -> None:
        selected = self.device_tree.selection()
        if not selected:
            self.selected_device_id = None
            return
        self.selected_device_id = int(selected[0])

    def update_selected_note(self) -> None:
        if self.selected_device_id is None:
            messagebox.showwarning("未选择设备", "请先在设备列表中选择一个设备。")
            return
        current_values = self.device_tree.item(str(self.selected_device_id), "values")
        current_note = str(current_values[1]) if current_values else ""
        note = simpledialog.askstring(
            "修改备注",
            "请输入设备备注，可留空：",
            initialvalue=current_note,
            parent=self.root,
        )
        if note is None:
            return
        self.database.update_device_note(self.selected_device_id, note.strip())
        self.refresh_devices()
        self.refresh_measurements()
        self._append_log("INFO", f"已更新设备 {self.selected_device_id} 的备注。")

    def delete_selected_device(self) -> None:
        if self.selected_device_id is None:
            messagebox.showwarning("未选择设备", "请先在设备列表中选择一个设备。")
            return

        confirmed = messagebox.askyesno(
            "确认删除设备",
            f"确定要删除设备 {self.selected_device_id} 吗？\n该设备的主密钥和关联采集数据都会被删除。",
        )
        if not confirmed:
            return

        deleted_device_id = self.selected_device_id
        self.database.delete_device(deleted_device_id)
        self.server.cache.clear()
        self.selected_device_id = None
        self.refresh_devices()
        self.refresh_measurements()
        self._append_log("WARNING", f"已删除设备 {deleted_device_id} 及其关联数据。")

    def export_selected_device(self) -> None:
        if self.selected_device_id is None:
            messagebox.showwarning("未选择设备", "请先在设备列表中选择一个设备。")
            return

        selected = self.device_tree.selection()
        if not selected:
            messagebox.showwarning("未选择设备", "请先在设备列表中选择一个设备。")
            return

        values = self.device_tree.item(selected[0], "values")
        device_id = str(values[0]).strip()
        master_key = str(values[2]).strip()

        chosen_dir = filedialog.askdirectory(title="选择设备目录")
        if not chosen_dir:
            return

        base_dir = Path(chosen_dir)
        target_dir = base_dir if base_dir.name == "encryptor" else base_dir / "encryptor"
        target_dir.mkdir(parents=True, exist_ok=True)

        (target_dir / "id").write_text(f"{device_id}\n", encoding="utf-8")
        (target_dir / "master_key").write_text(f"{master_key}\n", encoding="utf-8")

        self._append_log("INFO", f"已将设备 {device_id} 的凭据写入 {target_dir.as_posix()}")
        messagebox.showinfo(
            "写入完成",
            f"已覆盖写入以下文件：\n{target_dir / 'id'}\n{target_dir / 'master_key'}",
        )

    def import_device_from_directory(self) -> None:
        chosen_dir = filedialog.askdirectory(title="选择设备目录")
        if not chosen_dir:
            return

        base_dir = Path(chosen_dir)
        source_dir = base_dir if base_dir.name == "encryptor" else base_dir / "encryptor"
        id_path = source_dir / "id"
        key_path = source_dir / "master_key"

        if not id_path.exists() or not key_path.exists():
            messagebox.showerror(
                "导入失败",
                f"未找到以下文件：\n{id_path}\n{key_path}",
            )
            return

        try:
            device_id = int(id_path.read_text(encoding="utf-8").strip())
        except ValueError:
            messagebox.showerror("导入失败", f"{id_path} 中的设备 ID 无效。")
            return
        except OSError as exc:
            messagebox.showerror("导入失败", str(exc))
            return

        try:
            master_key_hex = key_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            messagebox.showerror("导入失败", str(exc))
            return

        try:
            record = self.database.import_device(device_id=device_id, master_key_hex=master_key_hex)
        except ValueError as exc:
            messagebox.showerror("导入失败", str(exc))
            return

        self.refresh_devices()
        self.refresh_measurements(show_errors=False)
        self._append_log("INFO", f"已从 {source_dir.as_posix()} 导入设备 {record.device_id}")
        messagebox.showinfo(
            "导入完成",
            f"设备ID: {record.device_id}\n主密钥: {record.master_key_hex}\n备注: {record.note or '(空)'}",
        )

    def clear_measurements(self) -> None:
        confirmed = messagebox.askyesno(
            "确认清空",
            "确定要清空所有采集数据吗？设备信息和主密钥不会被删除。",
        )
        if not confirmed:
            return
        self.database.clear_measurements()
        self.server.cache.clear()
        self.refresh_measurements()
        self._append_log("WARNING", "已清空所有采集数据。")

    def _on_close(self) -> None:
        self._save_state()
        self.server.close()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
