# Trulingo 🌍

Trulingo is a multilingual news aggregator and fact-checking tool that retrieves and processes articles from various news sources. It supports both English and Chinese news sources and can verify claims using the Gemini API.

## Features

- **Multilingual Support**: Aggregates news from both English and Chinese sources.
- **Claim Verification**: Uses the Gemini API to verify claims with context from both English and Chinese articles.
- **Streamlit UI**: Provides an interactive user interface for searching and verifying news claims.
- **Command Line Interface**: Allows searching and processing articles via the command line.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/NIC397/Trulingo.git
    ```

2. Change directory to the cloned folder and install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

### Streamlit App

To run the Streamlit app, use the following command:
```sh
streamlit run src/streamlit_app.py
```

### Command Line Interface
To use the command line interface, run:
```sh
python src/source_retrieval.py "Your claim here" -o output.json --gemini-key YOUR_GEMINI_API_KEY --verify --verbose
```

### Example Claims
You can test the tool with the following example claims:

- "MicroStrategy has benefited from the rally in cryptocurrencies this year"
- "AI models are getting better almost every month right now"
- "Sales of iPhone were up less than 1% in fiscal 2024 (which ended in September)"
- "The stock of Apple (NASDAQ: AAPL) is up 22% year to date in 2024"

### Project Structure
- `requirements.txt`: List of dependencies required for the project.
- `src/source_retrieval.py`: Main script for retrieving and processing articles.
- `src/streamlit_app.py`: Streamlit application for interactive use.

### Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

### License
This project is licensed under the MIT License. See the LICENSE file for details.

### Acknowledgements
This project was inspired by and uses templates from the [OrigINsight](https://github.com/Theod0reWu/OrigINsight) repository.