from flask import Flask
from api.resources import api_bp
# TODO: Import and initialize your sliding window rate limiter
# from core.middleware import RateLimiter

app = Flask(__name__)
app.register_blueprint(api_bp, url_prefix='/api')

@app.before_request
def apply_rate_limit():
    # TODO: Integrate the rate limiter here
    pass

if __name__ == "__main__":
    app.run(port=8080)
