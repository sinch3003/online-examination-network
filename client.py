"""
Student client for the TCP exam system (Person 2).

Usage:
    python client/client.py                      # asks for student ID, connects to 127.0.0.1:5050
    python client/client.py --host 192.168.1.5   # server on another machine
    python client/client.py --host 10.0.0.1 --port 5050 --id S101

Message format (one JSON object per line, ending with "\n"):
  client -> server: {"type": "hello",  "student_id": "S101"}
                    {"type": "answers", "answers": {"1": "B", "2": "C", "3": "A"}}
  server -> client: {"type": "questions", "duration": 120,
                     "items": [{"id": 1, "text": "...", "options": ["A. ...", "B. ..."]}]}
                    {"type": "result", "score": 8, "total": 10}
                    {"type": "error", "message": "..."}          (optional)
"duration" (seconds) is optional; if missing, DEFAULT_DURATION is used.
"""

import argparse
import json
import os
import socket
import threading
import time

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050
DEFAULT_DURATION = 300  # seconds, used if the server does not send "duration"
CONNECT_TIMEOUT = 5     # seconds to wait while connecting

lock = threading.Lock()
submitted = False


def send(f, obj):
    f.write(json.dumps(obj) + "\n")
    f.flush()


def recv(f):
    line = f.readline()
    if not line:
        raise ConnectionError("Server closed the connection.")
    msg = json.loads(line)
    if msg.get("type") == "error":
        raise RuntimeError("Server error: " + str(msg.get("message", "unknown")))
    return msg


def fmt_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def submit_and_show(f, answers):
    """Send answers once and print the result. Safe to call from two threads."""
    global submitted
    with lock:
        if submitted:
            return
        submitted = True
        print("\nSubmitting answers...")
        send(f, {"type": "answers", "answers": dict(answers)})
        print("Status: submitted. Waiting for result...")
        result = recv(f)
    print("\n==============================")
    print(f"  Your score: {result['score']} / {result['total']}")
    print("==============================")


def run_exam(f, student_id):
    send(f, {"type": "hello", "student_id": student_id})
    print("Status: connected, waiting for questions...")

    msg = recv(f)
    if msg.get("type") != "questions":
        raise RuntimeError(f"Unexpected message from server: {msg}")

    items = msg["items"]
    duration = msg.get("duration", DEFAULT_DURATION)
    deadline = time.time() + duration
    answers = {}

    print(f"\nExam started. {len(items)} questions, time limit {fmt_time(duration)}.")

    def on_timeout():
        print("\n\n*** TIME IS UP! Auto-submitting your answers. ***")
        try:
            submit_and_show(f, answers)
        except (ConnectionError, OSError, RuntimeError, ValueError) as e:
            print("Could not submit:", e)
        os._exit(0)  # stop the main thread even if it is waiting on input()

    timer = threading.Timer(duration, on_timeout)
    timer.daemon = True
    timer.start()

    for q in items:
        print(f"\n[Time left: {fmt_time(deadline - time.time())}]")
        print(f"Q{q['id']}. {q['text']}")
        for opt in q["options"]:
            print("   ", opt)
        while True:
            ans = input("Your answer (letter, Enter to skip): ").strip().upper()
            if ans == "" or ans[0].isalpha():
                break
            print("Please type a letter like A, B, C or D.")
        if ans:
            with lock:
                answers[str(q["id"])] = ans[0]

    timer.cancel()
    submit_and_show(f, answers)


def main():
    parser = argparse.ArgumentParser(description="Student exam client")
    parser.add_argument("--host", default=DEFAULT_HOST, help="server IP address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="server port")
    parser.add_argument("--id", dest="student_id", help="student ID")
    args = parser.parse_args()

    student_id = args.student_id or input("Enter student ID: ").strip()
    if not student_id:
        print("Student ID cannot be empty.")
        return

    print(f"Connecting to {args.host}:{args.port} ...")
    try:
        sock = socket.create_connection((args.host, args.port), timeout=CONNECT_TIMEOUT)
        sock.settimeout(None)  # no timeout once connected (student may think for a while)
    except ConnectionRefusedError:
        print("Could not connect: the server is not running or the port is wrong.")
        return
    except socket.timeout:
        print("Could not connect: timed out. Check the server IP and your network.")
        return
    except OSError as e:
        print("Could not connect:", e)
        return

    with sock:
        f = sock.makefile("rw", encoding="utf-8", newline="\n")
        try:
            run_exam(f, student_id)
        except (ConnectionError, ConnectionResetError, BrokenPipeError):
            print("\nLost connection to the server. Your exam could not be completed.")
        except RuntimeError as e:
            print("\n" + str(e))
        except (json.JSONDecodeError, KeyError) as e:
            print("\nReceived a message in an unexpected format:", e)
            print("Check the JSON format with Person 1.")
        except KeyboardInterrupt:
            print("\nExam cancelled.")


if __name__ == "__main__":
    main()
