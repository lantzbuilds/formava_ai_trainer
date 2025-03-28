 # AI Personal Trainer

This application integrates workout data from your weight training app with ChatGPT to create personalized workout routines based on your previous workouts and fitness goals.

## Features

- Reads workout data from your weight training app
- Processes the data and sends it to ChatGPT for analysis
- Receives personalized workout recommendations
- Sends the new workout routine back to your weight training app

## Setup

1. Clone this repository
2. Install dependencies using Pipenv:
   ```bash
   pipenv install
   ```
3. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```
4. Edit the `.env` file with your actual API keys and URLs

## Usage

Activate the virtual environment and run the main script:
```bash
pipenv shell
python main.py
```

## Development

To install development dependencies:
```bash
pipenv install --dev
```

## Configuration

The application requires the following environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `WORKOUT_APP_API_KEY`: Your weight training app API key
- `WORKOUT_APP_API_URL`: The base URL of your weight training app's API