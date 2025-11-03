from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import threading
import time
import grpc

import quiz_pb2 as pb
import quiz_pb2_grpc as rpc

ADDR = "127.0.0.1:50051"
LOCK = threading.Lock()

# In-memory state
ANSWERED: dict[tuple[str, str], tuple[str, bool]] = {}  # (player_id, question_id) -> (answer_id, correct)
SCORES: dict[str, int] = {}  # player_id -> total score

# Loaded from JSON
QUESTIONS: list[pb.Question] = []
ANSWER_KEY: dict[str, int] = {}  # question_id -> correct choice index


def _load_questions_from_json() -> tuple[list[pb.Question], dict[str, int]]:
    """Load questions from quiz/data/questions.json relative to this file."""
    data_path = Path(__file__).parent / "data" / "questions.json"
    with data_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if "questions" not in payload or not isinstance(payload["questions"], list):
        raise ValueError("questions.json: top-level 'questions' array is required")

    questions: list[pb.Question] = []
    answer_key: dict[str, int] = {}

    for i, q in enumerate(payload["questions"], start=1):
        try:
            qid = str(q["id"]).strip()
            text = str(q["text"])
            choices = list(q["choices"])
            correct_idx = int(q["answer_index"])
            seconds_left = int(q.get("seconds_left", 10))
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"questions.json: invalid question at index {i}: {e}")

        if not qid:
            raise ValueError(f"questions.json: empty id at index {i}")
        if not choices:
            raise ValueError(f"questions.json: choices must be non-empty for {qid}")
        if correct_idx < 0 or correct_idx >= len(choices):
            raise ValueError(f"questions.json: answer_index out of range for {qid}")

        questions.append(
            pb.Question(
                question_id=qid,
                text=text,
                choices=choices,
                seconds_left=seconds_left,
            )
        )
        answer_key[qid] = correct_idx

    return questions, answer_key


# Load once at import
QUESTIONS, ANSWER_KEY = _load_questions_from_json()


class QuizService(rpc.QuizServicer):
    def StreamQuestions(self, request: pb.Join, context):
        
        # If a client disconnects mid-game and reconnects later,
        # this tells the server which message sequence it last received.
        # This way, the server can resume streaming from the next question instead of starting over
        seq_start = int(request.last_seen_seq or 0) + 1
        seq = 0

        for idx, q in enumerate(QUESTIONS, start=1):
            seq = idx
            if seq < seq_start:
                continue
            # Each question is served immediately
            yield pb.ServerEvent(seq=seq, question=q)
            # For demonstration purposes, a 1 second delay is forced
            time.sleep(1.0) 

        # The client is informed that there are no more questions left in the round
        seq += 1
        yield pb.ServerEvent(seq=seq, round_end=pb.RoundEnd())

    def SubmitAnswer(self, request: pb.Answer, context):
        cur_total = SCORES.get(request.player_id, 0)

        # Basic validation
        if not request.player_id.strip():
            return pb.Ack(accepted=False, reason="invalid: empty player_id")
        if not request.game_id.strip():
            return pb.Ack(accepted=False, reason="invalid: empty game_id")
        if not request.question_id.strip():
            return pb.Ack(accepted=False, reason="invalid: empty question_id")
        if not request.answer_id.strip():
            return pb.Ack(accepted=False, reason="invalid: empty answer_id")
        if request.question_id not in ANSWER_KEY:
            return pb.Ack(accepted=False, reason="invalid: unknown question_id")

        # Choice bounds
        # Find question to validate choice range
        q = next((x for x in QUESTIONS if x.question_id == request.question_id), None)
        if q is None:
            return pb.Ack(accepted=False, reason="invalid: question not found")
        if request.choice_idx < 0 or request.choice_idx >= len(q.choices):
            return pb.Ack(accepted=False, reason="invalid: choice_idx out of range")

        key = (request.player_id, request.question_id)

        with LOCK:
            # Idempotency / duplicates
            if key in ANSWERED:
                prev_id, _prev_correct = ANSWERED[key]
                if prev_id == request.answer_id:
                    return pb.Ack(accepted=True, reason="duplicate")
                return pb.Ack(accepted=False, reason="duplicate")

            correct = (request.choice_idx == ANSWER_KEY[request.question_id])
            ANSWERED[key] = (request.answer_id, correct)
            if correct:
                SCORES[request.player_id] = SCORES.get(request.player_id, 0) + 1
            total = SCORES.get(request.player_id, 0)

        return pb.Ack(accepted=True, reason="ok", total=total)


def serve():
    server = grpc.server(ThreadPoolExecutor(max_workers=8))
    rpc.add_QuizServicer_to_server(QuizService(), server)
    server.add_insecure_port(ADDR)
    server.start()
    print(f"Quiz server running on {ADDR}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()