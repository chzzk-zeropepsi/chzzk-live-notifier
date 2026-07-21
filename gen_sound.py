# -*- coding: utf-8 -*-
"""알림음 생성 — notify.wav (마림바 느낌의 3음 상승 아르페지오).

소리를 바꾸고 싶으면 NOTES/tau 값을 수정하고 `python gen_sound.py` 재실행.
"""
import math
import struct
import wave

RATE = 44100
LENGTH_SEC = 1.1

# (시작 시각, 주파수 Hz, 감쇠 tau, 세기) — A5 → C#6 → E6 (A major 아르페지오)
NOTES = [
    (0.00, 880.00, 0.10, 0.85),
    (0.12, 1108.73, 0.11, 0.80),
    (0.24, 1318.51, 0.22, 1.00),
]

ATTACK = 0.004  # 4ms 어택 (클릭 노이즈 방지)


def note_sample(t: float, freq: float, tau: float, gain: float) -> float:
    if t < 0:
        return 0.0
    # 기음 + 배음 2개 (마림바처럼 배음은 빨리 사라짐)
    s = (
        math.sin(2 * math.pi * freq * t)
        + 0.35 * math.sin(2 * math.pi * freq * 2 * t) * math.exp(-t / (tau * 0.4))
        + 0.12 * math.sin(2 * math.pi * freq * 3 * t) * math.exp(-t / (tau * 0.25))
    )
    env = min(1.0, t / ATTACK) * math.exp(-t / tau)
    return s * env * gain


def main():
    n = int(RATE * LENGTH_SEC)
    samples = []
    for i in range(n):
        t = i / RATE
        v = sum(note_sample(t - start, f, tau, g) for start, f, tau, g in NOTES)
        samples.append(v)

    peak = max(abs(v) for v in samples)
    scale = 0.55 / peak  # 여유 있는 볼륨 (너무 크지 않게)

    with wave.open("notify.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(
            b"".join(struct.pack("<h", round(v * scale * 32767)) for v in samples)
        )
    print("saved: notify.wav")


if __name__ == "__main__":
    main()
