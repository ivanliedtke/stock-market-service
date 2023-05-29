from pytest import fixture
from unittest.mock import patch
import json
from dotenv import load_dotenv


@fixture(scope="session", autouse=True)
def load_env():
    load_dotenv("pytest.env", override=True)


@fixture
def client(scope="function"):
    from app import db, app

    app.config["TESTING"] = True

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


def test_signup(client):
    response = client.post(
        "/signup",
        json={
            "name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
        },
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert "api_key" in data
    assert len(data["api_key"]) > 0


def test_invalid_signup(client):
    response = client.post(
        "/signup",
        json={"name": "John", "last_name": "Doe", "email": "invalid-email"},
    )
    assert response.status_code == 400
    assert response.json["error"][0] == {
        "loc": ["email"],
        "msg": "value is not a valid email address",
        "type": "value_error.email",
    }


@patch("requests.get")
def test_stock_info(mock_get, client):
    from app import db, User, app

    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        "Meta Data": {},
        "Time Series (Daily)": {
            "2023-05-24": {
                "1. open": "120.0",
                "2. high": "122.0",
                "3. low": "109.0",
                "4. close": "110.0",
            },
            "2023-05-25": {
                "1. open": "110.0",
                "2. high": "111.0",
                "3. low": "99.0",
                "4. close": "100.0",
            },
        },
    }
    user = User(name="John", last_name="Doe", email="john.doe@example.com")
    user.api_key = "test-api-key"
    with app.app_context():
        db.session.add(user)
        db.session.commit()
        headers = {"API-Key": user.api_key}

    response = client.get("/stock-info?symbol=GOOGL", headers=headers)
    assert response.status_code == 200

    data = json.loads(response.data)
    assert data["symbol"] == "GOOGL"
    assert data["open_price"] == 110.0
    assert data["high_price"] == 111.0
    assert data["low_price"] == 99.0
    assert data["variation"] == -10.0


def test_stock_info_missing_api_key(client):
    response = client.get("/stock-info?symbol=GOOGL")
    assert response.status_code == 401
    assert response.json["error"] == "API key is missing"


def test_stock_info_invalid_api_key(client):
    headers = {"API-Key": "invalid-api-key"}
    response = client.get("/stock-info?symbol=GOOGL", headers=headers)
    assert response.status_code == 401
    assert response.json["error"] == "Invalid API key"


def test_stock_info_missing_symbol(client):
    from app import db, User

    user = User(name="John", last_name="Doe", email="john.doe@example.com")
    user.api_key = "test-api-key"
    db.session.add(user)
    db.session.commit()

    headers = {"API-Key": user.api_key}
    response = client.get("/stock-info", headers=headers)
    assert response.status_code == 400
    assert response.json["error"] == "Symbol is missing"


@patch("requests.get")
def test_stock_info_failed_request(mock_get, client):
    from app import db, User

    mock_get.return_value.status_code = 500
    mock_get.return_value.reason = "Mock Request Error"

    user = User(name="John", last_name="Doe", email="john.doe@example.com")
    user.api_key = "test-api-key"
    db.session.add(user)
    db.session.commit()

    headers = {"API-Key": user.api_key}
    response = client.get("/stock-info?symbol=GOOGL", headers=headers)
    assert response.status_code == 500
    assert (
        response.json["error"] == "Failed to retrieve stock info "
        "from Alpha Vantage: Mock Request Error"
    )


if __name__ == "__main__":
    import pytest

    pytest.main(["-vv"])
