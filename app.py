from secrets import token_urlsafe
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, List, Tuple, Union
from sqlalchemy.exc import IntegrityError
import requests
import traceback

from dotenv import load_dotenv
from flask import Flask, Response, redirect, request
from flask_sqlalchemy import SQLAlchemy
from pydantic import BaseModel, Field, ValidationError, EmailStr


load_dotenv()

# Setup logging
ENVIRONMENT = os.environ["ENVIRONMENT"]
if not os.path.exists("./logs"):
    os.mkdir("./logs")
logging.basicConfig(
    filename=f"./logs/{ENVIRONMENT}"
    f"-{datetime.now().strftime('%Y%m%d%H%M%S')}.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)

# Initiate Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DB_URI", "sqlite:///users.db"
)
db = SQLAlchemy(app)


class User(db.Model):
    """SQLAlchemy model for the users table"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(254), unique=True)
    api_key = db.Column(db.String(120), unique=True)

    def __init__(self, name: str, last_name: str, email: str):
        self.name = name
        self.last_name = last_name
        self.email = email
        self.api_key = token_urlsafe(16)


class SignupData(BaseModel):
    """Pydantic model for signup data validation"""

    name: str = Field(..., max_length=80)
    last_name: str = Field(..., max_length=80)
    email: EmailStr


request_timestamps: Dict[str, List[datetime]] = {}


def rate_limit():
    """Decorator for rate limiting by client IP"""

    def decorator(func):
        def wrapped(*args, **kwargs):
            client_ip = request.remote_addr or "LOCAL"

            # Check if client IP is present in the request timestamps dict
            if client_ip not in request_timestamps:
                request_timestamps[client_ip] = []

            current_time = datetime.now()

            # Remove timestamps older than 1 minute
            request_timestamps[client_ip] = [
                timestamp
                for timestamp in request_timestamps[client_ip]
                if timestamp > current_time - timedelta(minutes=1)
            ]

            # Check if rate limits are exceeded
            if len(request_timestamps[client_ip]) >= int(
                os.getenv("MAX_PER_MINUTE", 10)
            ) or (
                len(request_timestamps[client_ip])
                >= int(os.getenv("MAX_PER_SECOND", 1))
                and current_time - request_timestamps[client_ip][-1]
                < timedelta(seconds=1)
            ):
                return {
                    "error": "Too many requests. Please wait and try again."
                }, 429

            request_timestamps[client_ip].append(current_time)
            return func(*args, **kwargs)

        wrapped.__name__ = func.__name__
        return wrapped

    return decorator


@app.route("/")
def index():
    return redirect(
        "https://github.com/ivanliedtke/stock-market-service", code=302
    )


@app.route("/signup", methods=["POST"])
@rate_limit()
def signup() -> Tuple[Dict[str, Union[str, list]], int]:
    """Endpoint for user sign up"""
    try:
        data = SignupData(**request.json)
    except ValidationError as validation_error:
        return {"error": validation_error.errors()}, 400

    user = User(name=data.name, last_name=data.last_name, email=data.email)
    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        return {"error": "Email address already registered"}, 401

    return {"api_key": user.api_key}, 201


@app.route("/stock-info", methods=["GET"])
@rate_limit()
def stock_info() -> Tuple[Dict[str, Union[str, float]], int]:
    """Endpoint for retrieving stock information"""
    api_key = request.headers.get("API-Key")
    if not api_key:
        return {"error": "API key is missing"}, 401

    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        return {"error": "Invalid API key"}, 401

    symbol = request.args.get("symbol")
    if not symbol:
        return {"error": "Symbol is missing"}, 400

    url = str(
        "https://www.alphavantage.co/query"
        f"?function=TIME_SERIES_DAILY_ADJUSTED&symbol={symbol}"
        f"&outputsize=compact&apikey={os.environ['ALPHAVANTAGE_API_KEY']}"
    )
    response = requests.get(url, timeout=10)

    alpha_error = "Failed to retrieve stock info from Alpha Vantage: "
    if response.status_code != 200:
        return {"error": alpha_error + response.reason}, 500

    stock_data = response.json()

    if "Error Message" in stock_data:
        return {"error": alpha_error + stock_data["Error Message"]}, 500

    if "Note" in stock_data:
        return {"error": alpha_error + stock_data["Note"]}, 500

    # Extract the required information from the response
    time_series = stock_data["Time Series (Daily)"]
    previous_date, latest_date = sorted(time_series.keys())[-2:]
    previous_price = float(time_series[previous_date]["4. close"])
    latest_price = float(time_series[latest_date]["4. close"])

    return {
        "symbol": symbol,
        "open_price": float(time_series[latest_date]["1. open"]),
        "high_price": float(time_series[latest_date]["2. high"]),
        "low_price": float(time_series[latest_date]["3. low"]),
        "variation": round(latest_price - previous_price, 2),
    }, 200


@app.after_request
def log_request(response: Response) -> Response:
    """Logging middleware"""
    logging.info(f"{request.method} {request.url} {response.status_code}")
    logging.debug(f"Full Response: {response}")
    if traceback.format_exc() != "NoneType: None\n":
        logging.debug(f"Traceback: {traceback.format_exc()}")
    return response


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run()
