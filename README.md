# Stock Market Service

This is a REST API built with Flask that provides stock market information using the Alpha Vantage API. It also includes a user sign-up feature to generate API keys for accessing the API.

## Demo
A demo of this API is hosted at:

<a href="https://www.pythonanywhere.com"><img src="https://www.pythonanywhere.com/static/anywhere/images/PA-logo.svg" width="30%"></a>

Use https://ivanliedtke.pythonanywhere.com as your BASE_URL.

Please note that the demo URL may not be active or accessible depending on the deployment status.

## Usage
[![Run in Postman](https://run.pstmn.io/button.svg)](https://god.gw.postman.com/run-collection/27635916-ab76c115-8ec5-4618-ba3b-684de9608ad1?action=collection%2Ffork&source=rip_markdown&collection-url=entityId%3D27635916-ab76c115-8ec5-4618-ba3b-684de9608ad1%26entityType%3Dcollection%26workspaceId%3Dd8f57a46-e7dc-423d-aa78-82325be38289)

### Sign up for an API key
Send a POST request to *[BASE_URL]/signup* with the following JSON data:
```json
{
  "name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com"
}
```

You will receive a response containing your API key:
```json
{
  "api_key": "your-api-key"
}
```

### Get stock market information
Send a GET request to *[BASE_URL]/stock-info?symbol=[STOCK_SYMBOL]* with the following header:
- API-Key: *your-api-key*

Replace *your-api-key* with the API key obtained from the sign-up process.

The response will include the stock market information for the specified symbol:
- Open Price
- High Price
- Low Price
- Variation (previous day)

## Running Locally

### Prerequisites
- git
- Python 3.7+
- pip

### Clone the repository
```bash
git clone https://github.com/ivanliedtke/stock-market-service.git
```

### Create virtual env and install requirements
```bash
cd stock-market-service
[PYTHON_VERSION_PATH]/python.exe -m venv ./venv
venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Run the Flask application
First run will create the database in *./instance/users.db*
```bash
python app.py
```

### Start requesting!
Use http://localhost:5000 as your BASE_URL.


### Optional
Alter the configuration in the .env file
```properties
ENVIRONMENT=dev
LOG_LEVEL=DEBUG
DB_URI=sqlite:///users.db
MAX_PER_SECOND=1
MAX_PER_MINUTE=10
ALPHAVANTAGE_API_KEY=X86NOH6II01P7R24
```
