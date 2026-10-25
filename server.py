
import socket
import threading
import json

HOST = "0.0.0.0"
PORT = 5000

QUESTIONS = [
    {
        "id": 1,
        "question": "Which protocol provides reliable, ordered data delivery?",
        "options": ["A. UDP", "B. TCP", "C. HTTP", "D. ARP"],
        "answer": "B"
    },
    {
        "id": 2,
        "question": "Which function waits for an incoming TCP connection?",
        "options": ["A. send()", "B. connect()", "C. accept()", "D. close()"],
        "answer": "C"
    },
    {
        "id": 3,
        "question": "Which protocol is connection-oriented?",
        "options": ["A. TCP", "B. UDP", "C. IP", "D. DNS"],
        "answer": "A"
    }
]


def send_message(conn, message):
    data = json.dumps(message) + "\n"
    conn.sendall(data.encode("utf-8"))


def receive_message(file):
    line = file.readline()
    if not line:
        return None
    return json.loads(line)


def handle_client(conn, address):
    print(f"Connected: {address}")

    try:
        with conn:
            with conn.makefile("r", encoding="utf-8") as file:
                send_message(conn, {
                    "type": "questions",
                    "questions": [
                        {
                            "id": q["id"],
                            "question": q["question"],
                            "options": q["options"]
                        }
                        for q in QUESTIONS
                    ]
                })

                message = receive_message(file)

                if not message or message.get("type") != "answers":
                    send_message(conn, {
                        "type": "error",
                        "message": "Invalid answer submission."
                    })
                    return

                answers = message.get("answers", {})
                score = sum(
                    1 for q in QUESTIONS
                    if answers.get(str(q["id"]), "").strip().upper()
                    == q["answer"]
                )

                send_message(conn, {
                    "type": "result",
                    "score": score,
                    "total": len(QUESTIONS)
                })

                print(f"{address} scored {score}/{len(QUESTIONS)}")

    except (ConnectionError, json.JSONDecodeError, OSError) as error:
        print(f"Client error {address}: {error}")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()

        print(f"TCP exam server listening on port {PORT}...")

        while True:
            conn, address = server.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(conn, address),
                daemon=True
            )
            thread.start()


if __name__ == "__main__":
    main()
