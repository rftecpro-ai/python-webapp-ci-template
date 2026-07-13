from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello_world():
    return {"message": "Hello, World! Tag 1.0"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
