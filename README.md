# Quiz: gRPC Sample App
Example of a gRPC server and client using Python.

The server streams a series of questions with multiple answers (server to client streaming RPC). The client answers the said questions (client to server unary RPC).

The questions and answers are in `quiz/data/questions.json`.

## Installation
1. Create a Python virtual environment: `python -m venv venv`
2. Activate the said environment:
    - Windows: `venv\Scripts\activate` or `.\venv\Scripts\Activate`
    - Linux/Mac: `source venv/bin/activate`
3. Install the dependencies: `pip install -r requirements.txt`

## Instructions
1. Generate `quiz/quiz_pb2.py` and `quiz/quiz_pb2_grpc.py` from `proto/quiz.proto`:
```proto
python -m grpc_tools.protoc -Iproto \
  --python_out=quiz \
  --grpc_python_out=quiz \
  proto/quiz.proto
```
2. Run the server: `python quiz/server.py`
3. In different terminals, run clients: `python quiz/client.py` 
4. For each question answered, the client receives the current score
        
## Tools
Python

## Author
ChatGPT5, prompted by Arturo Mora-Rioja.