# -*- coding: utf-8 -*-
"""치지직 방송 알리미 — 팔로우한 스트리머가 방송을 켜면 Windows 알림을 보낸다."""
import json
import queue
import sys
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import chzzk_api

APP_NAME = "치지직 방송 알리미"
if getattr(sys, "frozen", False):  # PyInstaller exe
    BASE_DIR = Path(sys.executable).resolve().parent  # config.json, icons/ 저장 위치
    RES_DIR = Path(sys._MEIPASS)                      # 번들된 logo 등 리소스
else:
    BASE_DIR = RES_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ICON_DIR = BASE_DIR / "icons"

DEFAULT_CONFIG = {
    "poll_interval_sec": 30,
    "notify_on_startup": False,  # 앱 시작 시 이미 방송 중이어도 알림을 보낼지
    "use_windows_toast": False,  # True면 Windows 토스트, False면 자체 팝업(스팀 스타일)
    "popup_duration_sec": 8,     # 자체 팝업이 떠 있는 시간
    "sound_mode": "default",     # default(기본 알림음) | none(무음) | file(WAV 파일)
    "sound_file": "",            # sound_mode가 file일 때 재생할 .wav 경로
    "channels": [],
}


# ---------------------------------------------------------------- config

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------- toast icon

def cache_channel_icon(channel_id: str, image_url: str) -> str | None:
    """채널 프로필 이미지를 PNG로 변환해 저장하고 절대경로 반환 (토스트 아이콘용)."""
    if not image_url:
        return None
    path = ICON_DIR / f"{channel_id}.png"
    if path.exists():
        return str(path)
    try:
        ICON_DIR.mkdir(exist_ok=True)
        req = urllib.request.Request(image_url, headers=chzzk_api.HEADERS)
        raw = urllib.request.urlopen(req, timeout=10).read()
        from io import BytesIO

        from PIL import Image
        img = Image.open(BytesIO(raw))
        img.seek(0)  # GIF면 첫 프레임
        img = img.convert("RGBA").resize((96, 96))
        img.save(path, "PNG")
        return str(path)
    except Exception:
        return None


def send_toast(channel: dict, title: str, category: str, header: str | None = None) -> None:
    from winotify import Notification, audio
    name = channel["channelName"]
    cid = channel["channelId"]
    lines = [s for s in (title, category) if s]
    toast = Notification(
        app_id=APP_NAME,
        title=header or f"🔴 {name} 방송 시작!",
        msg="\n".join(lines) or "방송이 시작되었습니다.",
        icon=((cache_channel_icon(cid, channel.get("channelImageUrl", "")) if cid else None)
              or (str(RES_DIR / "logo.png") if (RES_DIR / "logo.png").exists() else "")),
        launch=chzzk_api.live_url(cid) if cid else "https://chzzk.naver.com",
    )
    toast.set_audio(audio.Default, loop=False)
    toast.show()


# ---------------------------------------------------------------- 자체 팝업 (스팀 스타일)

def work_area() -> tuple[int, int, int, int]:
    """작업 표시줄을 제외한 화면 영역 (left, top, right, bottom)."""
    import ctypes
    import ctypes.wintypes
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right, rect.bottom


class LivePopup(tk.Toplevel):
    """우하단에 슬라이드 인 → 잠시 후 사라지는 알림 팝업. 클릭하면 방송 열림."""

    ACTIVE: list["LivePopup"] = []
    W, H, GAP, MARGIN = 348, 96, 10, 14
    BG, MINT, GREY = "#15171c", "#00dea0", "#9aa0a6"

    def __init__(self, app: "App", channel: dict, header: str, subtitle: str):
        super().__init__(app.root)
        self.app = app
        self.cid = channel.get("channelId") or ""
        self.withdraw()
        self.overrideredirect(True)  # 테두리 없는 창
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.configure(bg=self.MINT)  # 1px 민트 테두리

        inner = tk.Frame(self, bg=self.BG)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        photo = app.get_popup_photo(self.cid)
        pic = tk.Label(inner, bg=self.BG, image=photo)
        pic.image = photo  # GC 방지
        pic.pack(side="left", padx=(12, 10))

        texts = tk.Frame(inner, bg=self.BG)
        texts.pack(side="left", fill="x", expand=True, pady=12)
        tk.Label(texts, text=channel.get("channelName", ""), bg=self.BG, fg="white",
                 font=("Malgun Gothic", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(texts, text=header, bg=self.BG, fg=self.MINT,
                 font=("Malgun Gothic", 9), anchor="w").pack(fill="x")
        if subtitle:
            if len(subtitle) > 24:
                subtitle = subtitle[:24] + "…"
            tk.Label(texts, text=subtitle, bg=self.BG, fg=self.GREY,
                     font=("Malgun Gothic", 9), anchor="w").pack(fill="x")

        close_btn = tk.Label(inner, text="✕", bg=self.BG, fg=self.GREY,
                             font=("Malgun Gothic", 9), cursor="hand2")
        close_btn.place(relx=1.0, x=-8, y=6, anchor="ne")
        close_btn.bind("<Button-1>", lambda e: self.close())

        for w in (inner, pic, texts, *texts.winfo_children()):
            w.configure(cursor="hand2")
            w.bind("<Button-1>", self.on_click)

        LivePopup.ACTIVE.append(self)
        self.slide_in()
        stay_ms = max(2, int(app.config.get("popup_duration_sec", 8))) * 1000
        self.after(stay_ms, self.fade_out)

    def target_pos(self) -> tuple[int, int]:
        idx = LivePopup.ACTIVE.index(self)
        left, top, right, bottom = work_area()
        x = right - self.W - self.MARGIN
        y = bottom - self.MARGIN - (idx + 1) * self.H - idx * self.GAP
        return x, y

    def slide_in(self):
        x, y = self.target_pos()
        self.geometry(f"{self.W}x{self.H}+{x + 48}+{y}")
        self.deiconify()
        self._animate(0, x + 48, x, y)

    def _animate(self, step: int, x0: int, x1: int, y: int, steps: int = 12):
        if not self.winfo_exists():
            return
        t = (step + 1) / steps
        ease = 1 - (1 - t) ** 3  # ease-out
        self.geometry(f"{self.W}x{self.H}+{round(x0 + (x1 - x0) * ease)}+{y}")
        self.attributes("-alpha", min(1.0, t * 1.3))
        if step + 1 < steps:
            self.after(15, lambda: self._animate(step + 1, x0, x1, y, steps))

    def fade_out(self):
        if not self.winfo_exists():
            return
        alpha = float(self.attributes("-alpha"))
        if alpha <= 0.08:
            self.close()
        else:
            self.attributes("-alpha", alpha - 0.08)
            self.after(30, self.fade_out)

    def on_click(self, *_):
        if self.cid:
            webbrowser.open(chzzk_api.live_url(self.cid))
        self.close()

    def close(self):
        if self in LivePopup.ACTIVE:
            LivePopup.ACTIVE.remove(self)
        try:
            self.destroy()
        except Exception:
            pass
        for p in LivePopup.ACTIVE:  # 남은 팝업들 아래로 정렬
            if p.winfo_exists():
                x, y = p.target_pos()
                p.geometry(f"{p.W}x{p.H}+{x}+{y}")


# ---------------------------------------------------------------- poller

class Poller(threading.Thread):
    """팔로우 목록을 주기적으로 확인해서 OFF→ON 전환 시 알림을 쏜다."""

    def __init__(self, app: "App"):
        super().__init__(daemon=True)
        self.app = app
        self.stop_event = threading.Event()
        self.wake_event = threading.Event()  # '지금 새로고침'용
        self.live_state: dict[str, bool | None] = {}  # channelId -> 마지막 openLive

    def run(self):
        while not self.stop_event.is_set():
            self.poll_once()
            interval = max(10, int(self.app.config.get("poll_interval_sec", 30)))
            self.wake_event.wait(timeout=interval)
            self.wake_event.clear()

    def poll_once(self):
        for channel in list(self.app.config["channels"]):
            if self.stop_event.is_set():
                return
            cid = channel["channelId"]
            try:
                info = chzzk_api.get_channel(cid)
            except Exception as e:
                self.app.events.put(("error", cid, str(e), None))
                continue
            is_live = bool(info.get("openLive"))
            prev = self.live_state.get(cid)
            self.live_state[cid] = is_live

            title = category = ""
            if is_live:
                detail = chzzk_api.get_live_status(cid)
                title = detail.get("liveTitle") or ""
                category = detail.get("liveCategoryValue") or ""

            self.app.events.put(("status", cid, is_live, title))

            first_check = prev is None
            went_live = is_live and (prev is False)
            startup_live = is_live and first_check and self.app.config.get("notify_on_startup")
            if went_live or startup_live:
                # 알림은 GUI 스레드에서 처리 (팝업 창 생성은 메인 스레드 전용)
                self.app.events.put(("notify", channel, title, category))
        self.app.events.put(("polled", None, None, None))

    def refresh_now(self):
        self.wake_event.set()

    def forget(self, cid: str):
        self.live_state.pop(cid, None)


# ---------------------------------------------------------------- GUI

class App:
    def __init__(self):
        self.config = load_config()
        self.events: queue.Queue = queue.Queue()
        self.search_results: list[dict] = []
        self.search_iid_by_cid: dict[str, str] = {}
        self.tree_icons: dict[str, object] = {}  # channelId -> PhotoImage (GC 방지 참조 유지)
        self.tray_icon = None

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("560x720")
        self.root.minsize(480, 560)
        ico = RES_DIR / "logo.ico"
        if ico.exists():
            try:
                self.root.iconbitmap(default=str(ico))
            except Exception:
                pass
        self.build_ui()

        self.poller = Poller(self)
        self.poller.start()
        self.root.after(300, self.drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.start_tray()

    # -------- UI 구성
    def build_ui(self):
        pad = {"padx": 8, "pady": 4}
        ttk.Style().configure("Treeview", rowheight=32)  # 프로필 이미지 들어갈 높이

        search_frame = ttk.LabelFrame(self.root, text="스트리머 검색")
        search_frame.pack(fill="x", **pad)

        row = ttk.Frame(search_frame)
        row.pack(fill="x", padx=6, pady=6)
        self.search_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.search_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.do_search())
        ttk.Button(row, text="검색", command=self.do_search).pack(side="left", padx=(6, 0))

        self.search_tree = ttk.Treeview(
            search_frame, columns=("name", "followers", "live"),
            show="tree headings", height=5,
        )
        self.search_tree.heading("name", text="채널명")
        self.search_tree.heading("followers", text="팔로워")
        self.search_tree.heading("live", text="방송중")
        self.search_tree.column("#0", width=44, stretch=False)  # 프로필 이미지
        self.search_tree.column("name", width=220)
        self.search_tree.column("followers", width=90, anchor="e")
        self.search_tree.column("live", width=70, anchor="center")
        self.search_tree.pack(fill="x", padx=6, pady=(0, 6))
        self.search_tree.bind("<Double-1>", lambda e: self.add_selected())

        ttk.Button(search_frame, text="＋ 알림 목록에 추가 (더블클릭도 가능)",
                   command=self.add_selected).pack(padx=6, pady=(0, 8), anchor="e")

        # 상태 바를 먼저 bottom에 배치 → 창이 작아져도 잘리지 않음
        self.status_var = tk.StringVar(value="시작 중…")
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", side="bottom")
        ttk.Label(bar, textvariable=self.status_var, anchor="w").pack(
            side="left", fill="x", expand=True, padx=8, pady=4
        )

        # 설정 패널 (상태 바 위)
        settings = ttk.LabelFrame(self.root, text="설정")
        settings.pack(fill="x", side="bottom", padx=8, pady=(0, 2))

        row1 = ttk.Frame(settings)
        row1.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(row1, text="새로고침 주기(초)").pack(side="left")
        self.poll_var = tk.StringVar(value=str(self.config["poll_interval_sec"]))
        sp1 = ttk.Spinbox(row1, from_=10, to=600, increment=5, width=5,
                          textvariable=self.poll_var, command=self.save_settings)
        sp1.pack(side="left", padx=(4, 18))
        ttk.Label(row1, text="팝업 유지(초)").pack(side="left")
        self.dur_var = tk.StringVar(value=str(self.config["popup_duration_sec"]))
        sp2 = ttk.Spinbox(row1, from_=2, to=60, width=4,
                          textvariable=self.dur_var, command=self.save_settings)
        sp2.pack(side="left", padx=4)
        for sp in (sp1, sp2):
            sp.bind("<FocusOut>", lambda e: self.save_settings())
            sp.bind("<Return>", lambda e: self.save_settings())

        row2 = ttk.Frame(settings)
        row2.pack(fill="x", padx=6, pady=(2, 8))
        ttk.Label(row2, text="알림 소리").pack(side="left")
        self.sound_var = tk.StringVar(value=self.sound_mode_label())
        combo = ttk.Combobox(row2, textvariable=self.sound_var, state="readonly",
                             width=9, values=("기본 알림음", "무음", "WAV 파일"))
        combo.pack(side="left", padx=4)
        combo.bind("<<ComboboxSelected>>", lambda e: self.on_sound_mode())
        ttk.Button(row2, text="파일 선택…", command=self.pick_sound_file).pack(side="left", padx=(6, 0))
        ttk.Button(row2, text="▶ 미리듣기", command=self.play_sound).pack(side="left", padx=6)
        self.sound_file_var = tk.StringVar(value=Path(self.config["sound_file"]).name
                                           if self.config.get("sound_file") else "")
        ttk.Label(row2, textvariable=self.sound_file_var, foreground="#888").pack(
            side="left", padx=4
        )

        follow_frame = ttk.LabelFrame(self.root, text="알림 받는 스트리머")
        follow_frame.pack(fill="both", expand=True, **pad)

        # 버튼 줄을 목록보다 먼저 bottom에 배치 → 목록이 줄어들지 버튼은 안 잘림
        btns = ttk.Frame(follow_frame)
        btns.pack(fill="x", side="bottom", padx=6, pady=(0, 8))
        ttk.Button(btns, text="방송 열기", command=self.open_selected).pack(side="left")
        ttk.Button(btns, text="제거", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(btns, text="지금 새로고침", command=self.poller_refresh).pack(side="left")
        ttk.Button(btns, text="🔔 알림 테스트", command=self.test_notification).pack(side="right")

        self.follow_tree = ttk.Treeview(
            follow_frame, columns=("name", "status", "title"),
            show="tree headings",
        )
        self.follow_tree.heading("name", text="채널명")
        self.follow_tree.heading("status", text="상태")
        self.follow_tree.heading("title", text="방송 제목")
        self.follow_tree.column("#0", width=44, stretch=False)  # 프로필 이미지
        self.follow_tree.column("name", width=140)
        self.follow_tree.column("status", width=80, anchor="center")
        self.follow_tree.column("title", width=210)
        self.follow_tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.follow_tree.tag_configure("live", foreground="#d32f2f")
        self.follow_tree.bind("<Double-1>", lambda e: self.open_selected())

        self.reload_follow_tree()

    # -------- 검색
    def do_search(self):
        keyword = self.search_var.get().strip()
        if not keyword:
            return
        self.status_var.set(f"'{keyword}' 검색 중…")
        threading.Thread(target=self._search_worker, args=(keyword,), daemon=True).start()

    def _search_worker(self, keyword: str):
        try:
            results = chzzk_api.search_channels(keyword)
        except Exception as e:
            self.events.put(("search_error", None, str(e), None))
            return
        self.events.put(("search_done", None, results, None))

    def show_search_results(self, results: list[dict]):
        self.search_results = results
        self.search_tree.delete(*self.search_tree.get_children())
        self.search_iid_by_cid = {}
        for i, ch in enumerate(results):
            name = ch["channelName"] + (" ✔" if ch["verifiedMark"] else "")
            self.search_iid_by_cid[ch["channelId"]] = str(i)
            self.search_tree.insert(
                "", "end", iid=str(i),
                image=self.get_photo(ch["channelId"]) or "",
                values=(name, f'{ch["followerCount"]:,}', "🔴" if ch["openLive"] else ""),
            )
        self.status_var.set(f"검색 결과 {len(results)}개")
        self.fetch_icons(results)

    def add_selected(self):
        sel = self.search_tree.selection()
        if not sel:
            return
        ch = self.search_results[int(sel[0])]
        if any(c["channelId"] == ch["channelId"] for c in self.config["channels"]):
            self.status_var.set(f'{ch["channelName"]} 은(는) 이미 목록에 있습니다.')
            return
        self.config["channels"].append({
            "channelId": ch["channelId"],
            "channelName": ch["channelName"],
            "channelImageUrl": ch["channelImageUrl"],
        })
        save_config(self.config)
        self.reload_follow_tree()
        self.fetch_icons([ch])  # 프로필 이미지를 추가 시점에 바로 저장
        self.poller_refresh()
        self.status_var.set(f'{ch["channelName"]} 추가됨 — 상태 확인 중…')

    # -------- 팔로우 목록
    def reload_follow_tree(self):
        self.follow_tree.delete(*self.follow_tree.get_children())
        for ch in self.config["channels"]:
            self.follow_tree.insert(
                "", "end", iid=ch["channelId"],
                image=self.get_photo(ch["channelId"]) or "",
                values=(ch["channelName"], "확인 중…", ""),
            )
        self.fetch_icons(self.config["channels"])

    def remove_selected(self):
        sel = self.follow_tree.selection()
        if not sel:
            return
        cid = sel[0]
        self.config["channels"] = [
            c for c in self.config["channels"] if c["channelId"] != cid
        ]
        save_config(self.config)
        self.poller.forget(cid)
        self.reload_follow_tree()
        self.poller_refresh()

    def open_selected(self):
        sel = self.follow_tree.selection()
        if sel:
            webbrowser.open(chzzk_api.live_url(sel[0]))

    def poller_refresh(self):
        self.poller.refresh_now()

    # -------- 채널 프로필 이미지
    def get_photo(self, cid: str):
        """캐시된 아이콘 PNG를 목록 표시용 PhotoImage로 로드."""
        if cid in self.tree_icons:
            return self.tree_icons[cid]
        path = ICON_DIR / f"{cid}.png"
        if not path.exists():
            return None
        try:
            from PIL import Image, ImageTk
            photo = ImageTk.PhotoImage(Image.open(path).resize((28, 28)))
            self.tree_icons[cid] = photo
            return photo
        except Exception:
            return None

    def fetch_icons(self, channels: list[dict]):
        """아직 저장 안 된 프로필 이미지를 백그라운드로 내려받아 icons/에 저장."""
        missing = [
            ch for ch in channels
            if ch["channelId"] not in self.tree_icons
            and not (ICON_DIR / f'{ch["channelId"]}.png').exists()
        ]
        if not missing:
            return

        def worker():
            for ch in missing:
                if cache_channel_icon(ch["channelId"], ch.get("channelImageUrl", "")):
                    self.events.put(("icon", ch["channelId"], None, None))

        threading.Thread(target=worker, daemon=True).start()

    # -------- 설정
    def save_settings(self):
        def to_int(var, lo, hi, fallback):
            try:
                return max(lo, min(hi, int(var.get())))
            except ValueError:
                return fallback

        self.config["poll_interval_sec"] = to_int(
            self.poll_var, 10, 600, self.config["poll_interval_sec"])
        self.config["popup_duration_sec"] = to_int(
            self.dur_var, 2, 60, self.config["popup_duration_sec"])
        self.poll_var.set(str(self.config["poll_interval_sec"]))
        self.dur_var.set(str(self.config["popup_duration_sec"]))
        save_config(self.config)
        self.status_var.set(
            f'설정 저장됨 — 주기 {self.config["poll_interval_sec"]}초, '
            f'팝업 {self.config["popup_duration_sec"]}초'
        )

    def sound_mode_label(self) -> str:
        return {"none": "무음", "file": "WAV 파일"}.get(
            self.config.get("sound_mode", "default"), "기본 알림음")

    def on_sound_mode(self):
        mode = {"기본 알림음": "default", "무음": "none", "WAV 파일": "file"}[self.sound_var.get()]
        if mode == "file" and not self.config.get("sound_file"):
            self.pick_sound_file()  # 파일이 없으면 바로 선택창
            return
        self.config["sound_mode"] = mode
        save_config(self.config)
        self.status_var.set(f"알림 소리: {self.sound_var.get()}")

    def pick_sound_file(self):
        path = filedialog.askopenfilename(
            title="알림 소리로 쓸 WAV 파일 선택",
            filetypes=[("WAV 파일", "*.wav")],
        )
        if not path:
            self.sound_var.set(self.sound_mode_label())  # 취소 시 원래대로
            return
        self.config["sound_mode"] = "file"
        self.config["sound_file"] = path
        save_config(self.config)
        self.sound_var.set("WAV 파일")
        self.sound_file_var.set(Path(path).name)
        self.status_var.set(f"알림 소리: {Path(path).name}")

    def play_sound(self):
        mode = self.config.get("sound_mode", "default")
        if mode == "none":
            return
        try:
            import winsound
            if mode == "file" and self.config.get("sound_file") \
                    and Path(self.config["sound_file"]).exists():
                winsound.PlaySound(
                    self.config["sound_file"],
                    winsound.SND_FILENAME | winsound.SND_ASYNC,
                )
            else:
                winsound.PlaySound(
                    "Notification.Default", winsound.SND_ALIAS | winsound.SND_ASYNC
                )
        except Exception:
            pass

    # -------- 알림
    def get_popup_photo(self, cid: str):
        """팝업용 56px 프로필 이미지. 없으면 앱 로고로 대체."""
        key = f"popup:{cid}"
        if key in self.tree_icons:
            return self.tree_icons[key]
        path = ICON_DIR / f"{cid}.png"
        if not cid or not path.exists():
            path = RES_DIR / "logo.png"
        if not path.exists():
            return None
        try:
            from PIL import Image, ImageTk
            photo = ImageTk.PhotoImage(Image.open(path).resize((56, 56)))
            self.tree_icons[key] = photo
            return photo
        except Exception:
            return None

    def notify(self, channel: dict, title: str, category: str, header: str | None = None):
        """GUI 스레드에서 호출. 설정에 따라 자체 팝업 또는 Windows 토스트."""
        if self.config.get("use_windows_toast"):
            threading.Thread(
                target=send_toast, args=(channel, title, category, header), daemon=True
            ).start()
            return
        self.play_sound()
        subtitle = " · ".join(s for s in (title, category) if s)
        LivePopup(self, channel, header or "🔴 방송을 시작했습니다", subtitle)

    def test_notification(self):
        sel = self.follow_tree.selection()
        if sel:
            ch = next(
                (c for c in self.config["channels"] if c["channelId"] == sel[0]), None
            )
        elif self.config["channels"]:
            ch = self.config["channels"][0]
        else:
            ch = {"channelId": "", "channelName": APP_NAME, "channelImageUrl": ""}
        self.notify(
            ch, "실제 방송이 켜지면 이렇게 알림이 옵니다.", "",
            header="🔔 알림 테스트 — 클릭하면 방송이 열려요",
        )
        self.status_var.set(f'{ch["channelName"]} 테스트 알림을 보냈습니다.')

    # -------- 이벤트 처리 (폴링/검색 스레드 → GUI)
    def drain_events(self):
        try:
            while True:
                kind, cid, a, b = self.events.get_nowait()
                if kind == "status":
                    if self.follow_tree.exists(cid):
                        is_live, title = a, b
                        self.follow_tree.item(
                            cid,
                            values=(
                                self.follow_tree.set(cid, "name"),
                                "🔴 LIVE" if is_live else "⚫ 오프라인",
                                title,
                            ),
                            tags=("live",) if is_live else (),
                        )
                elif kind == "polled":
                    self.status_var.set(
                        time.strftime("마지막 확인: %H:%M:%S")
                        + f' (주기 {self.config["poll_interval_sec"]}초)'
                    )
                elif kind == "search_done":
                    self.show_search_results(a)
                elif kind == "search_error":
                    self.status_var.set(f"검색 실패: {a}")
                elif kind == "icon":
                    photo = self.get_photo(cid)
                    if photo:
                        iid = self.search_iid_by_cid.get(cid)
                        if iid and self.search_tree.exists(iid):
                            self.search_tree.item(iid, image=photo)
                        if self.follow_tree.exists(cid):
                            self.follow_tree.item(cid, image=photo)
                elif kind == "notify":
                    self.notify(cid, a, b)  # cid 자리에 channel dict가 들어옴
                elif kind == "error":
                    self.status_var.set(f"확인 실패({cid[:8]}…): {a}")
        except queue.Empty:
            pass
        self.root.after(300, self.drain_events)

    # -------- 트레이
    def start_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            return  # 트레이 없이도 동작

        logo = RES_DIR / "logo.png"
        if logo.exists():
            img = Image.open(logo)
        else:  # 로고 파일이 없으면 즉석에서 그린 폴백 아이콘
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse((4, 4, 60, 60), fill=(0, 222, 160, 255))
            d.polygon([(26, 20), (26, 44), (46, 32)], fill=(255, 255, 255, 255))

        menu = pystray.Menu(
            pystray.MenuItem("열기", self.show_window, default=True),
            pystray.MenuItem("지금 새로고침", lambda: self.poller_refresh()),
            pystray.MenuItem("종료", self.quit_app),
        )
        self.tray_icon = pystray.Icon("chzzk_notifier", img, APP_NAME, menu)
        self.tray_icon.run_detached()

    def show_window(self, *_):
        self.root.after(0, lambda: (self.root.deiconify(), self.root.lift()))

    def hide_to_tray(self):
        if self.tray_icon:
            self.root.withdraw()  # 트레이로 최소화, 폴링은 계속
        else:
            self.quit_app()

    def quit_app(self, *_):
        self.poller.stop_event.set()
        self.poller.refresh_now()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
