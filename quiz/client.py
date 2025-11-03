import uuid
import grpc

import quiz_pb2 as pb
import quiz_pb2_grpc as rpc

ADDR = "127.0.0.1:50051"

def run():
    player_id = input("Player ID: ").strip() or "player1"
    game_id = "demo"

    channel = grpc.insecure_channel(ADDR)
    stub = rpc.QuizStub(channel)

    print("Subscribing to questions...")
    stream = stub.StreamQuestions(pb.Join(player_id=player_id, game_id=game_id, last_seen_seq=0))

    for ev in stream:
        if ev.HasField("question"):
            q = ev.question
            print(f"\nQ[{ev.seq}] {q.text}")
            for i, choice in enumerate(q.choices):
                print(f"  {i}: {choice}")

            while True:
                raw = input("Your choice index: ").strip()
                if not raw.isdigit():
                    print("Please enter a number.")
                    continue
                choice_idx = int(raw)
                break

            ack = stub.SubmitAnswer(pb.Answer(
                player_id=player_id,
                game_id=game_id,
                question_id=q.question_id,
                answer_id=str(uuid.uuid4()),
                choice_idx=choice_idx
            ))
            status = "accepted" if ack.accepted else "rejected"
            print(f"{status} ({ack.reason}) - score: {ack.total}")

        elif ev.HasField("round_end"):
            print("\nRound finished.")

    channel.close()

if __name__ == "__main__":
    run()