📰 NewsVision
Version 2.0
Advanced Smart News Scraper GUI – Built with PyQt6 & BeautifulSoup

📌 Overview
NewsVision is a professional-grade, GUI-based news headline scraper developed using Python, PyQt6, Requests, and BeautifulSoup. It is designed for journalists, developers, researchers, and data analysts who need fast and intelligent access to online news headlines.

The app provides a smooth, modular interface that allows users to test URLs, detect headlines, adjust scraping parameters, and troubleshoot common scraping issues — all without writing a single line of code.

🚀 Key Features
✅ Scraper Tab: Smart headline extraction with browser-mimicking headers

🧪 URL Tester: Diagnose accessibility and scraping issues of any news URL

📊 Results Tab: View structured scraped headlines and analysis

⚙️ Settings Tab: Control request timeout, delays, and data behavior

🧰 Troubleshooting Tools: 403 error handling, common fixes, and built-in test results viewer

🌐 Multiple Selectors Support: Auto-detects headline tags (h1, h2, .title, .headline, etc.)

🧠 Indian Express RSS Fallback: Smart feed integration for specific news sites

🖥️ Custom Splash Screen: Polished launch animation with progress steps

💾 Save Settings: Persists session and layout across runs

🧰 Technologies Used
Technology	Purpose
Python 3.10+	Core backend logic
PyQt6	Graphical User Interface (GUI)
Requests	HTTP requests
BeautifulSoup	HTML parsing and extraction
Threading	Background scraping without UI freezing

📂 Project Structure
bash
Copy
Edit
NewsVision/
├── assets/              # Icons and splash visuals
├── news.py              # Main GUI application
├── README.md            # Project documentation
├── requirements.txt     # Python package requirements
🧪 Demo
Module	Description
Scraper	Enter a URL and begin headline extraction
Settings	Adjust scraping timeouts and intervals
Results	View structured extracted content
Analytics	(Future Scope) NLP-based headline clustering

📥 Installation & Setup
Clone the repository

bash
Copy
Edit
git clone https://github.com/yourusername/NewsVision.git
cd NewsVision
(Optional) Create and activate a virtual environment

bash
Copy
Edit
python -m venv venv
venv\Scripts\activate  # Windows
Install the required packages

bash
Copy
Edit
pip install -r requirements.txt
Run the application

bash
Copy
Edit
python news.py
✅ Requirements
Python 3.10+

PyQt6

requests

beautifulsoup4

If requirements.txt is missing, you can install manually:

bash
Copy
Edit
pip install PyQt6 requests beautifulsoup4
📊 Sample Use Case
Test URL: https://indianexpress.com/section/india/

Auto-detects headline structure

Scrapes and previews top news headlines

Alerts if scraping is blocked (403, RSS fallback offered)

🔧 Troubleshooting Tips
Issue	Solution
403 Forbidden	Use VPN or test with headers
Timeout Errors	Increase timeout in settings
No Results	Manually check selectors
Specific Sites (e.g., Indian Express)	Use RSS feed fallback

📌 Future Enhancements
 Multi-site batch scraping

 NLP-powered headline clustering

 Export scraped data to CSV/JSON

 Dark mode interface

 Plug-in system for new news sites


🛡️ Disclaimer
NewsVision is intended for educational and research purposes only. Scrape responsibly and ensure compliance with each website’s terms of service.

