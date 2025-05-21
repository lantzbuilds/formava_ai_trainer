# AI Personal Trainer

An intelligent workout planning and tracking application that uses AI to generate personalized workout routines based on user preferences, experience level, and medical considerations.

## Features

- **AI-Powered Workout Generation**: Creates personalized workout routines using OpenAI's GPT-4
- **Exercise Search**: Semantic search through exercise database using vector embeddings
- **Injury-Aware Planning**: Considers user injuries and medical conditions when generating routines
- **Hevy Integration**: Syncs generated workouts with Hevy workout tracking app
- **User Profiles**: Stores user preferences, experience level, and medical information
- **Workout History**: Tracks past workouts and progress

## Architecture

The application is built using Python and consists of several key components:

- **Streamlit Frontend**: Web interface for user interaction
- **OpenAI Service**: Handles workout generation and AI recommendations
- **Vector Store**: Stores and searches exercise data using embeddings
- **Database**: Stores user profiles, workout history, and exercise data
- **Hevy API Integration**: Syncs workouts with the Hevy app

### Key Components

- `app.py`: Main application entry point
- `services/openai_service.py`: Handles AI-powered workout generation
- `services/vector_store.py`: Manages exercise search functionality
- `services/hevy_api.py`: Handles Hevy API integration
- `config/database.py`: Database connection and operations
- `pages/`: Contains different application pages (workout history, AI recommendations)

## Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai_personal_trainer.git
   cd ai_personal_trainer
   ```

2. **Install dependencies**
   ```bash
   pipenv install
   ```

3. **Set up environment variables**
   Create a `.env` file with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   MONGODB_URI=your_mongodb_uri
   ```

4. **Initialize the vector store**
   ```bash
   python scripts/recreate_vector_store.py
   ```

5. **Run the application**
   ```bash
   pipenv run streamlit run app.py
   ```

## Usage

1. **Create a User Profile**
   - Enter your experience level
   - Specify any injuries or medical conditions
   - Set your fitness goals
   - Configure workout preferences

2. **Generate Workouts**
   - Select workout focus (e.g., full body, upper body)
   - Choose experience level
   - Set workout duration
   - Generate personalized routine

3. **Track Progress**
   - View workout history
   - Track exercise performance
   - Monitor progress over time

## Development

### Adding New Exercises

To add new exercises to the vector store:

1. Add exercise data to the database
2. Run the vector store recreation script:
   ```bash
   python scripts/recreate_vector_store.py
   ```

### Testing

Run the test suite:
```bash
pipenv run pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.