from __future__ import annotations

import argparse
import time
from typing import Any

import cv2

from live_client import FaceDemoClient


WINDOW_NAME = "Python Face Demo Live"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local live camera demo for liveness + face recognition.")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="Face demo server base URL.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index.")
    parser.add_argument("--interval-ms", type=int, default=500, help="Frame upload interval in milliseconds.")
    parser.add_argument("--threshold", type=float, default=None, help="Optional recognition threshold override.")
    parser.add_argument("--width", type=int, default=0, help="Optional capture width.")
    parser.add_argument("--height", type=int, default=0, help="Optional capture height.")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP request timeout in seconds.")
    return parser.parse_args()


def draw_text_block(frame: Any, lines: list[str]) -> Any:
    output = frame.copy()
    y = 30
    for index, line in enumerate(lines):
        color = (0, 255, 0)
        if "REJECT" in line or "error" in line.lower() or "failed" in line.lower():
            color = (0, 0, 255)
        elif "SKIPPED" in line or "No result" in line:
            color = (0, 215, 255)

        cv2.putText(
            output,
            line,
            (20, y + index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            output,
            line,
            (20, y + index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            1,
            cv2.LINE_AA,
        )
    return output


def format_result_lines(result: dict[str, Any] | None, server: str, interval_ms: int) -> list[str]:
    lines = [
        f"Server: {server}",
        f"Interval: {interval_ms} ms",
        "Press q to quit.",
    ]
    if result is None:
        lines.append("No result yet.")
        return lines

    if not result.get("requestOk"):
        lines.append(f"Last error: {result.get('message', 'Unknown error')}")
        return lines

    matched = "YES" if result.get("matched") else "NO"
    lines.extend(
        [
            f"Liveness: {result.get('livenessResult', '-')}",
            f"LivenessScore: {result.get('livenessScore', '-')}",
            f"Matched: {matched}",
            f"EmployeeNo: {result.get('employeeNo') or '-'}",
            f"EmployeeName: {result.get('employeeName') or '-'}",
            f"Similarity: {result.get('similarity', '-')}",
            f"ElapsedMs: {result.get('elapsedMs', '-')}",
            f"Message: {result.get('message', '-')}",
        ]
    )
    return lines


def try_enable_preview() -> bool:
    try:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        return True
    except cv2.error:
        return False


def main() -> int:
    args = parse_args()
    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        print(f"Failed to open camera index {args.camera}.")
        return 1

    if args.width > 0:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    if args.height > 0:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    client = FaceDemoClient(server_url=args.server, timeout_seconds=args.timeout)
    latest_result: dict[str, Any] | None = None
    last_request_monotonic = 0.0
    preview_enabled = try_enable_preview()

    if not preview_enabled:
        print("Preview window is not available in the current OpenCV build. Running in console mode.")

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                print("Failed to read frame from camera.")
                return 1

            now = time.monotonic()
            if now - last_request_monotonic >= args.interval_ms / 1000.0:
                latest_result = client.recognize_frame(frame_bgr=frame, threshold=args.threshold)
                last_request_monotonic = now
                print(latest_result)

            overlay = draw_text_block(
                frame=frame,
                lines=format_result_lines(
                    result=latest_result,
                    server=args.server,
                    interval_ms=args.interval_ms,
                ),
            )

            if preview_enabled:
                try:
                    cv2.imshow(WINDOW_NAME, overlay)
                except cv2.error:
                    preview_enabled = False
                    print("Preview window is not supported by the current OpenCV package. Switched to console mode.")

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
