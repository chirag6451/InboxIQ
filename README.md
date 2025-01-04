# AI-Email-Classifier

An intelligent email classification and management system that uses AI to analyze, categorize, and forward emails based on their content and priority.

## Features

- **AI-Powered Email Analysis**: Uses OpenAI's GPT models to understand email content
- **Smart Categorization**: Automatically categorizes emails into predefined categories
- **Priority Assignment**: Assigns priority levels (Urgent, High, Normal, Low)
- **Action Item Detection**: Identifies and extracts action items from emails
- **Email Forwarding**: Forwards emails to appropriate recipients based on categories
- **Detailed Reporting**: Generates comprehensive reports including:
  - Email summaries
  - Category statistics
  - Consolidated action items
  - Processing statistics

## Requirements

- Python 3.10+
- Gmail API credentials
- OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:chirag6451/AI-Email-Classifier.git
   cd AI-Email-Classifier
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export OPENAI_MODEL="gpt-3.5-turbo"
   ```

4. Configure Gmail API credentials:
   - Place your `credentials.json` in the project root directory
   - Run the application once to generate token.json

## Usage

Run the email processor:
```bash
python process_emails.py
```

The system will:
1. Fetch unread emails from your Gmail account
2. Analyze and categorize each email
3. Forward emails based on configured rules
4. Generate a detailed report

## Configuration

Edit `config.py` to customize:
- Email categories and their descriptions
- Priority levels
- Forwarding rules
- Spam detection settings

## Project Structure

- `process_emails.py`: Main entry point
- `email_analyzer.py`: Email content analysis
- `email_classifier.py`: AI-based classification
- `gmail_handler.py`: Gmail API interactions
- `report_generator.py`: Report generation
- `config.py`: System configuration

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

## License

MIT License

## Author

Chirag Ahmedabadi