# Talky - Voice-Driven Intelligent Agent

Talky is an intelligent voice-driven AI assistant built for Telegram that uses advanced AI reasoning, natural language processing, and automated task planning to help users accomplish various tasks through natural conversation. It combines speech recognition, intent classification, optimal planning algorithms, and multi-service integration to provide a seamless, human-like interaction experience.

## Features

### Voice & Text Interface
- **Voice Messages**: Send voice commands via Telegram - the bot transcribes and processes them
- **Text Commands**: Type commands naturally in plain English
- **Voice Responses**: Bot responds with both text and voice (using OpenAI TTS or Google TTS)
- **Image Recognition**: Analyze and describe images using Ollama Llava vision model
- **Web UI**: Modern chat interface with real-time messaging, voice input, and image upload

### Intelligent Understanding
- **Natural Language Processing**: Understands conversational, natural language (not just commands)
- **Intent Classification**: Uses GPT-4 to classify user intents with confidence scoring
- **Context Awareness**: Remembers conversation context and handles follow-up questions
- **Multi-Intent Detection**: Can handle multiple intents in a single message
- **Ambiguity Resolution**: Automatically resolves similar intents (e.g., Greeting vs SmallTalk)
- **Capability Questions**: Hardcoded responses for "what can you do" type questions

### Smart Planning & Execution
- **A* Search Algorithm**: Uses optimal pathfinding to plan action sequences
- **Multi-Step Planning**: Breaks down complex requests into actionable steps
- **Dependency Management**: Handles actions that depend on other actions
- **Parallel Execution**: Executes independent actions simultaneously when possible
- **Direct Execution**: Simple intents (todos) bypass planning for faster response

### Academic Integration (Bennett University ERP)
- **Attendance Tracking**: Check attendance for any subject or monthly overview
- **Timetable Management**: View class schedules and subject timetables
- **Cafeteria Menu**: Get daily menu for breakfast, lunch, dinner, and snacks
- **PDF Reports**: Generate and email PDF reports of attendance, timetable, or cafeteria data

### Internet & Information
- **Web Search**: Search the internet using Perplexity API with OpenAI summarization
- **Context-Aware Follow-ups**: Understands references from previous search results
- **Concise Answers**: All responses limited to under 500 words

### Communication
- **Email Sending**: Send formatted emails using SMTP (Gmail)
- **PDF Email Reports**: Automatically email PDF reports when requested
- **OpenAI Formatting**: Professional email formatting using OpenAI
- **Auto Email Detection**: Automatically sends email if "email" or "mail" keywords are mentioned

### Task Management
- **Todo List**: Add, list, complete, and delete tasks
- **Supabase Storage**: Persistent todo storage with Supabase
- **Status Tracking**: Track pending and completed tasks
- **Web & Telegram**: Manage todos from both web UI and Telegram

### Other Features
- **Weather Information**: Check weather for any location
- **Conversational AI**: Natural conversations using OpenAI
- **Follow-up Questions**: Understands pronouns and references
- **Explainable AI**: Transparent decision-making with audit trails

## Requirements

- Python 3.11 or 3.12
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key (for GPT-4, Whisper, and TTS)
- Supabase Project (for database)
- Perplexity API Key (for internet search)
- (Optional) Ollama with Llava model (for local image recognition)
- FFmpeg (for audio processing)

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd talky
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Set up Supabase database:**

Run the SQL script in `supabase_setup.sql` to create all required tables:
- `user_sessions` - User session management
- `interaction_history` - Command and response history
- `audit_logs` - AI decision audit trail
- `web_chat_history` - Web UI chat history
- `todo_list` - Todo task management

6. **Install FFmpeg** (required for audio processing):
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`

7. **Set up Llava Flask Server (Optional, for remote image recognition):**
```bash
python llava_flask_server.py
# Server will automatically create ngrok tunnel and save URL to npoint.io
```

## Configuration

Edit the `.env` file with your credentials:

### Required
- `TELEGRAM_BOT_TOKEN`: Get from [@BotFather](https://t.me/botfather)
- `OPENAI_API_KEY`: Get from [OpenAI Platform](https://platform.openai.com/)
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/public key
- `PERPLEXITY_API_KEY`: Get from [Perplexity](https://www.perplexity.ai/)

### Optional
- `USER_EMAIL`: Default email for "send to me" requests
- `EMAIL_HOST`: SMTP host (default: smtp.gmail.com)
- `EMAIL_PORT`: SMTP port (default: 587)
- `EMAIL_USER`: SMTP username
- `EMAIL_PASS`: SMTP password
- `USE_NGROK_URL`: Set to "true" to use remote Llava server via ngrok, "false" for local Ollama
- `NPOINT_API_URL`: npoint.io API endpoint for ngrok URL exchange
- `OLLAMA_BASE_URL`: Local Ollama server URL (default: http://localhost:11434)
- `LLAVA_REMOTE_URL`: Remote Llava server URL (if using ngrok)

## Usage

### Telegram Bot

1. **Start the bot:**
```bash
python main.py
```

2. **Interact with the bot:**
   - Find your bot on Telegram (search for the bot username)
   - Send `/start` to begin
   - Send voice messages or text commands like:
     - "What's my attendance?"
     - "Email me my timetable report"
     - "Search for information about AI"
     - "Add going to ethics class to my todo list"
     - "What can you do?"

### Web UI

1. **Start the web server:**
```bash
python web_ui.py
```

2. **Access the web interface:**
   - Open browser to `http://localhost:5001`
   - Features:
     - Text chat interface
     - Voice message input
     - Image upload and analysis
     - Chat history sidebar
     - Dashboard for statistics
     - Settings page
     - Landing page

## Project Structure

```
talky/
├── main.py                      # Main Telegram bot entry point
├── web_ui.py                    # Flask web UI server
├── llava_flask_server.py        # Llava image recognition server
├── config.py                    # Configuration management
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project metadata
├── supabase_setup.sql           # Database schema
├── PROJECT_OVERVIEW.md          # Detailed project documentation
├── speech/                      # Speech processing
│   ├── stt_processor.py        # Speech-to-text (OpenAI Whisper)
│   └── tts_processor.py        # Text-to-speech (OpenAI TTS/gTTS)
├── nlp/                         # Natural language processing
│   ├── intent_classifier.py    # Intent classification (GPT-4)
│   └── nlp_utils.py            # NLP utilities (follow-ups, entities)
├── planning/                    # Planning system
│   ├── knowledge_base.py       # Action definitions and rules
│   ├── astar_planner.py        # A* search algorithm
│   └── state_manager.py        # State management
├── execution/                   # Action execution
│   ├── action_executor.py       # Execution engine
│   ├── api_clients.py          # API clients (ERP, Email, Weather, etc.)
│   └── image_client.py         # Image recognition client
├── explainability/              # Explainable AI
│   ├── explanation_engine.py   # Explanation generation
│   └── audit_logger.py         # Audit logging to Supabase
├── utils/                       # Utilities
│   ├── database.py             # Supabase integration
│   ├── audio_utils.py          # Audio conversion utilities
│   └── pdf_generator.py        # PDF report generation
└── templates/                   # Web UI templates
    ├── index.html              # Main chat interface
    ├── landing.html            # Landing page
    ├── dashboard.html          # Dashboard page
    └── settings.html           # Settings page
└── static/                      # Web UI static files
    ├── css/style.css           # Styles
    ├── js/app.js               # Client-side JavaScript
    └── images/                  # Images and logos
```

## Architecture

### Core Components

1. **Telegram Interface** (`main.py`): Handles voice and text messages from Telegram
2. **Web Interface** (`web_ui.py`): Flask-SocketIO web server for browser-based chat
3. **Speech Processing** (`speech/`): STT (Whisper) and TTS (OpenAI/gTTS)
4. **Intent Classification** (`nlp/intent_classifier.py`): Probabilistic reasoning with GPT-4
5. **Planning System** (`planning/`): A* search for optimal action sequences
6. **Execution Engine** (`execution/`): Executes planned actions via APIs
7. **Explainability** (`explainability/`): Generates human-readable explanations
8. **Image Recognition** (`llava_flask_server.py`): Llava model server for image analysis

### AI Algorithms

- **Probabilistic Intent Classification**: Uses GPT-4 with confidence scoring
- **A* Search**: Optimal pathfinding for action planning
- **State Space Search**: Models world state and transitions
- **Context-Aware NLP**: Follow-up question detection and pronoun resolution

### Workflow

See `WORKFLOW_DIAGRAM.svg` for a detailed visual representation of the complete system workflow.

## Example Use Cases

### Simple (Single Action)
**Input**: "Check weather in Mumbai"
**Processing**: Intent=CheckWeather, Parameter=Mumbai
**Execution**: Weather API call
**Output**: "Mumbai weather: Sunny, 28°C, light winds"

### Academic Query
**Input**: "What's my attendance for this month?"
**Processing**: Intent=CheckMonthlyAttendance
**Execution**: ERP API call → Format with OpenAI
**Output**: "Your attendance for this month is 85%. You attended 17 out of 20 classes."

### Multi-Step with Email
**Input**: "Make a report about my attendance and email it to me"
**Processing**: Intent=GenerateAttendancePDF + SendEmail
**Execution**: Fetch attendance → Generate PDF → Format email → Send
**Output**: "Generated attendance report. Email sent successfully to [email]."

### Internet Search
**Input**: "Search for information about Bennett University"
**Processing**: Intent=SearchInternet
**Execution**: Perplexity search → OpenAI summarization
**Output**: Concise summary under 500 words

### Todo Management
**Input**: "Add going to ethics class to my todo list"
**Processing**: Intent=AddTodo
**Execution**: Direct execution (no planning) → Save to Supabase
**Output**: "Added todo: going to ethics class"

### Capability Question
**Input**: "What can you do?"
**Processing**: Detected capability keywords → Hardcoded response
**Output**: Comprehensive list of all features

## Testing

Run unit tests (when available):
```bash
pytest tests/
```

## Performance Requirements

- Voice processing: < 5 seconds end-to-end latency
- Intent classification: > 85% accuracy
- Planning algorithm: < 2 seconds for up to 10 actions
- Concurrent user support: 50+ simultaneous sessions
- Response limit: All OpenAI responses under 500 words

## Security & Privacy

- Input validation and sanitization
- API key protection via environment variables
- User data encryption via Supabase
- Session isolation and cleanup
- Rate limiting and abuse prevention
- No emojis in responses (clean text output)

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg and ensure it's in your PATH
2. **Supabase connection error**: Check your SUPABASE_URL and SUPABASE_KEY
3. **OpenAI API error**: Verify your API key and check rate limits
4. **Audio conversion fails**: Ensure audio file format is supported
5. **Llava image recognition timeout**: Increase timeout or use remote server
6. **Perplexity 401 error**: Verify API key is correctly set
7. **Email sending fails**: Check SMTP credentials and USER_EMAIL configuration

## Contributing

This is a college project. Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All new features include tests
- Documentation is updated
- No emojis in code or responses (use plain text)

## License

This project is for educational purposes.

## Acknowledgments

- OpenAI for GPT-4, Whisper, and TTS APIs
- Perplexity for search API
- Supabase for database infrastructure
- python-telegram-bot library
- Flask and Flask-SocketIO for web UI
- Ollama for local LLM support

## Future Enhancements

- [ ] Add more action types
- [ ] Improve multi-intent handling
- [ ] Add user authentication
- [ ] Implement conversation context persistence
- [ ] Add performance metrics dashboard
- [ ] Support for more languages
- [ ] Webhook deployment option
- [ ] Mobile app integration
