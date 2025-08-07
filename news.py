#!/usr/bin/env python3
"""
Professional News Headlines Scraper
A modern PyQt6 application for scraping news headlines from various sources
Enhanced Professional Version with Improved UI/UX
"""

import sys
import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import threading
import time
import webbrowser
from urllib.parse import urljoin, urlparse
import csv

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QPushButton, QLabel, QComboBox, QTableWidget, 
    QTableWidgetItem, QTextEdit, QProgressBar, QSplitter,
    QGroupBox, QCheckBox, QSpinBox, QLineEdit, QTabWidget,
    QFileDialog, QMessageBox, QStatusBar, QHeaderView,
    QFrame, QScrollArea, QGridLayout, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSettings, 
    QPropertyAnimation, QEasingCurve, QRect
)
from PyQt6.QtGui import (
    QFont, QPalette, QColor, QIcon, QPixmap, 
    QLinearGradient, QBrush, QAction, QKeySequence
)


class NewsSource:
    """Class to define news source configurations"""
    def __init__(self, name, url, selectors):
        self.name = name
        self.url = url
        self.selectors = selectors  # List of CSS selectors to try


class ScraperThread(QThread):
    """Background thread for scraping operations"""
    progress_update = pyqtSignal(int)
    headline_found = pyqtSignal(dict)  # {title, url, source, timestamp}
    finished_scraping = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, sources, max_headlines=50):
        super().__init__()
        self.sources = sources
        self.max_headlines = max_headlines
        self.is_running = True
        
    def run(self):
        """Main scraping logic"""
        all_headlines = []
        total_sources = len(self.sources)
        
        for i, source in enumerate(self.sources):
            if not self.is_running:
                break
                
            try:
                headlines = self.scrape_source(source)
                all_headlines.extend(headlines)
                
                # Emit progress
                progress = int((i + 1) / total_sources * 100)
                self.progress_update.emit(progress)
                
                # Small delay between requests
                time.sleep(0.5)
                
            except Exception as e:
                self.error_occurred.emit(f"Error scraping {source.name}: {str(e)}")
        
        self.finished_scraping.emit(all_headlines)
    
    def scrape_source(self, source):
        """Scrape headlines from a single source with enhanced anti-bot protection"""
        headlines = []
        
        try:
            # Enhanced headers to bypass anti-bot protection
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Referer': source.url if source.url else 'https://www.google.com/'
            }
            
            # Create a session for cookie management
            session = requests.Session()
            session.headers.update(headers)
            
            # Special handling for Indian websites that might have anti-bot protection
            if 'indianexpress.com' in source.url or 'timesofindia.indiatimes.com' in source.url:
                # Add additional delay for Indian sites
                time.sleep(2)
                
                # Try to get the page with multiple attempts
                max_attempts = 3
                response = None
                
                for attempt in range(max_attempts):
                    try:
                        response = session.get(source.url, timeout=15, allow_redirects=True)
                        if response.status_code == 200:
                            break
                        elif response.status_code == 403:
                            # If blocked, try with different user agent
                            session.headers.update({
                                'User-Agent': f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
                            })
                            time.sleep(3)  # Wait longer between attempts
                        else:
                            time.sleep(1)
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            raise e
                        time.sleep(2)
                
                if not response or response.status_code != 200:
                    raise Exception(f"Failed to access {source.name} after {max_attempts} attempts. Status: {response.status_code if response else 'No response'}")
                    
            else:
                response = session.get(source.url, timeout=10, allow_redirects=True)
                
            response.raise_for_status()
            
            # Parse with different parsers if needed
            soup = None
            try:
                soup = BeautifulSoup(response.content, 'lxml')
            except:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                except:
                    soup = BeautifulSoup(response.content, 'html5lib')
            
            if not soup:
                raise Exception("Failed to parse HTML content")
            
            # Try different selectors for this source
            elements = []
            for selector in source.selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        break
                except Exception as selector_error:
                    continue
            
            # If no elements found with CSS selectors, try alternative methods
            if not elements:
                # Try finding headlines in common patterns
                alternative_selectors = [
                    'a[href*="news"]', 'a[href*="story"]', 'a[href*="article"]',
                    '.headline', '.title', '.news-title', '.story-headline',
                    'h1 a', 'h2 a', 'h3 a', 'h4 a',
                    '[class*="headline"]', '[class*="title"]', '[class*="story"]'
                ]
                
                for alt_selector in alternative_selectors:
                    try:
                        elements = soup.select(alt_selector)
                        if elements:
                            break
                    except:
                        continue
            
            count = 0
            processed_titles = set()  # To avoid duplicates
            
            for element in elements:
                if count >= self.max_headlines:
                    break
                    
                title = ""
                # Try different ways to extract title
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    title = element.get_text().strip()
                elif element.name == 'a':
                    title = element.get_text().strip()
                    if not title:
                        # Try getting title from nested elements
                        nested = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div'])
                        if nested:
                            title = nested.get_text().strip()
                else:
                    title = element.get_text().strip()
                
                # Clean up title
                title = ' '.join(title.split())  # Remove extra whitespace
                
                # Skip if title is too short, empty, or duplicate
                if not title or len(title) < 15 or title in processed_titles:
                    continue
                
                # Skip if title looks like navigation or ads
                skip_patterns = ['Home', 'News', 'Sports', 'Business', 'Opinion', 'Entertainment',
                               'Login', 'Subscribe', 'Advertisement', 'More', 'Latest', 'Breaking',
                               'Top Stories', 'Read More', 'View All', 'Load More']
                
                if any(pattern.lower() in title.lower() for pattern in skip_patterns) and len(title) < 30:
                    continue
                
                processed_titles.add(title)
                
                # Try to get the link
                link = None
                if element.name == 'a':
                    link = element.get('href')
                else:
                    link_element = element.find('a')
                    if link_element:
                        link = link_element.get('href')
                
                # Make link absolute
                if link and not link.startswith('http'):
                    from urllib.parse import urljoin
                    link = urljoin(source.url, link)
                
                headline_data = {
                    'title': title,
                    'url': link or source.url,
                    'source': source.name,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                headlines.append(headline_data)
                self.headline_found.emit(headline_data)
                count += 1
                
        except requests.exceptions.RequestException as e:
            if "403" in str(e) or "Forbidden" in str(e):
                raise Exception(f"Access denied to {source.name}. The website may be blocking automated requests. Try using a VPN or contact the site for API access.")
            elif "timeout" in str(e).lower():
                raise Exception(f"Timeout connecting to {source.name}. The website may be slow or unreachable.")
            else:
                raise Exception(f"Network error accessing {source.name}: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to scrape {source.name}: {str(e)}")
        
        return headlines
    
    def stop(self):
        """Stop the scraping process"""
        self.is_running = False


class ModernTableWidget(QTableWidget):
    """Custom table widget with modern styling and proper visibility"""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #2c3e50;
                alternate-background-color: #f8f9fa;
                selection-background-color: #3498db;
                selection-color: #ffffff;
                gridline-color: #dee2e6;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border: none;
                border-bottom: 1px solid #f1f3f4;
                color: #2c3e50;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #e8f4fd;
                color: #2c3e50;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: #ffffff;
                padding: 12px 8px;
                border: none;
                border-right: 1px solid #2c3e50;
                font-weight: 600;
                font-size: 12px;
            }
            QHeaderView::section:hover {
                background-color: #2c3e50;
            }
        """)


class NewsScraperApp(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.headlines = []
        self.scraper_thread = None
        self.settings = QSettings('NewsScraperApp', 'Settings')
        
        # Define news sources
        self.news_sources = [
            NewsSource("BBC News", "https://www.bbc.com/news", 
                      ["h3", ".media__title a", ".gs-c-promo-heading__title"]),
            NewsSource("Reuters", "https://www.reuters.com", 
                      ["h3 a", ".story-title", "h2 a"]),
            NewsSource("CNN", "https://www.cnn.com", 
                      ["h3 a", ".cd__headline-text", "h2 a"]),
            NewsSource("The Guardian", "https://www.theguardian.com", 
                      [".fc-item__title a", "h3 a", ".u-faux-block-link__overlay"]),
            NewsSource("Associated Press", "https://apnews.com", 
                      [".PagePromo-title a", "h1 a", "h2 a"]),
            NewsSource("Indian Express", "https://indianexpress.com/section/india/", 
                      [".title a", "h2 a", "h3 a", ".ie-custom-story-item h3 a", ".story-details h3 a"]),
            NewsSource("Times of India", "https://timesofindia.indiatimes.com/india", 
                      [".content a", "h2 a", "h3 a", ".story-list h3 a"]),
            NewsSource("Hindustan Times", "https://www.hindustantimes.com/india-news", 
                      [".hdg3 a", "h3 a", ".story-title", ".big-news h3 a"]),
            NewsSource("NDTV", "https://www.ndtv.com/india", 
                      [".nstory_header a", "h2 a", "h3 a", ".story-title"]),
            NewsSource("India Today", "https://www.indiatoday.in/india", 
                      [".detail h3 a", "h2 a", "h3 a", ".story-kicker"])
        ]
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Professional News Headlines Scraper v2.0")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 700)
        
        # Set application icon (you can add an icon file)
        self.setWindowIcon(QIcon())
        
        # Apply modern theme
        self.apply_modern_theme()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create header
        self.create_header(main_layout)
        
        # Create tab widget for different sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 10px;
                background-color: #ffffff;
                padding: 5px;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                min-width: 100px;
                border: 1px solid #dee2e6;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: #ffffff;
                border-color: #3498db;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e9ecef;
                color: #343a40;
            }
        """)
        
        # Create tabs
        self.create_scraper_tab()
        self.create_results_tab()
        self.create_settings_tab()
        self.create_analytics_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Create status bar
        self.create_status_bar()
        
        # Setup timer for auto-refresh
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.start_scraping)
        
    def apply_modern_theme(self):
        """Apply modern professional color scheme and styling"""
        palette = QPalette()
        
        # Professional color scheme
        palette.setColor(QPalette.ColorRole.Window, QColor(248, 249, 250))  # Light background
        palette.setColor(QPalette.ColorRole.WindowText, QColor(44, 62, 80))  # Dark text
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))  # White input backgrounds
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(241, 243, 244))  # Alternate row
        palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))  # Button background
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(44, 62, 80))  # Button text
        palette.setColor(QPalette.ColorRole.Text, QColor(44, 62, 80))  # Input text
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))  # Bright text
        palette.setColor(QPalette.ColorRole.Highlight, QColor(52, 152, 219))  # Selection background
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))  # Selected text
        
        self.setPalette(palette)
        
        # Set professional font
        font = QFont("Segoe UI", 10)
        self.setFont(font)
        
        # Apply comprehensive professional stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            
            QWidget {
                color: #2c3e50;
                background-color: transparent;
            }
            
            QLabel {
                color: #2c3e50;
                font-size: 12px;
                font-weight: 500;
                padding: 4px 2px;
            }
            
            QPushButton {
                background-color: #3498db;
                color: #ffffff;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                min-width: 120px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background-color: #21618c;
                transform: translateY(0px);
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            
            QPushButton#danger {
                background-color: #e74c3c;
            }
            QPushButton#danger:hover {
                background-color: #c0392b;
            }
            
            QPushButton#success {
                background-color: #27ae60;
            }
            QPushButton#success:hover {
                background-color: #229954;
            }
            
            QPushButton#warning {
                background-color: #f39c12;
                color: #ffffff;
            }
            QPushButton#warning:hover {
                background-color: #e67e22;
            }
            
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                margin-top: 20px;
                padding-top: 15px;
                background-color: #ffffff;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #34495e;
                font-weight: 600;
                font-size: 14px;
                background-color: #ffffff;
            }
            
            QComboBox {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 25px;
            }
            QComboBox:hover {
                border-color: #3498db;
            }
            QComboBox:focus {
                border-color: #3498db;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #7f8c8d;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #2c3e50;
                selection-background-color: #3498db;
                selection-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 6px;
            }
            
            QLineEdit {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 12px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #3498db;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #bdc3c7;
            }
            
            QSpinBox {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                min-height: 25px;
            }
            QSpinBox:focus {
                border-color: #3498db;
            }
            QSpinBox:hover {
                border-color: #bdc3c7;
            }
            
            QCheckBox {
                color: #2c3e50;
                font-size: 12px;
                font-weight: 500;
                spacing: 10px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #dee2e6;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:hover {
                border-color: #3498db;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #3498db;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQiIGhlaWdodD0iMTQiIHZpZXdCb3g9IjAgMCAxNCAxNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTExLjY2NjcgMy41TDUuMjUgOS45MTY2N0wyLjMzMzM0IDciIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }
            
            QTextEdit {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
            
            QProgressBar {
                background-color: #ecf0f1;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                height: 25px;
                text-align: center;
                color: #2c3e50;
                font-weight: 600;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 8px;
            }
            
            QStatusBar {
                background-color: #ffffff;
                color: #2c3e50;
                border-top: 1px solid #dee2e6;
                font-size: 11px;
                padding: 5px;
            }
            
            QTreeWidget {
                background-color: #ffffff;
                color: #2c3e50;
                alternate-background-color: #f8f9fa;
                selection-background-color: #3498db;
                selection-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 8px;
                border: none;
                border-bottom: 1px solid #f1f3f4;
            }
            QTreeWidget::item:selected {
                background-color: #3498db;
                color: #ffffff;
            }
            QTreeWidget::item:hover:!selected {
                background-color: #e8f4fd;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: #ffffff;
                padding: 10px;
                border: none;
                border-right: 1px solid #2c3e50;
                font-weight: 600;
                font-size: 12px;
            }
            
            QScrollBar:vertical {
                background-color: #f8f9fa;
                width: 14px;
                border-radius: 7px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background-color: #bdc3c7;
                border-radius: 7px;
                min-height: 25px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #95a5a6;
            }
            
            QScrollBar:horizontal {
                background-color: #f8f9fa;
                height: 14px;
                border-radius: 7px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background-color: #bdc3c7;
                border-radius: 7px;
                min-width: 25px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #95a5a6;
            }
        """)
        
    def create_header(self, layout):
        """Create application header with title and logo"""
        header_frame = QFrame()
        header_frame.setFixedHeight(90)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2c3e50, stop:1 #34495e);
                border-radius: 12px;
                margin-bottom: 10px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(25, 15, 25, 15)
        
        # Left side - Icon and title
        left_layout = QHBoxLayout()
        
        # Icon
        icon_label = QLabel("📰")
        icon_label.setStyleSheet("""
            color: #ffffff;
            font-size: 32px;
            margin-right: 15px;
        """)
        
        # Title and subtitle
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_label = QLabel("NewsVision")
        title_label.setStyleSheet("""
            color: #ffffff;
            font-size: 24px;
            font-weight: 700;
            margin: 0;
            padding: 0;
        """)
        
        subtitle_label = QLabel("Advanced web scraping tool for news aggregation")
        subtitle_label.setStyleSheet("""
            color: #bdc3c7;
            font-size: 14px;
            font-weight: 400;
            margin: 0;
            padding: 0;
        """)
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        left_layout.addWidget(icon_label)
        left_layout.addLayout(title_layout)
        
        # Right side - Version and status
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        version_label = QLabel("Version 2.0 Professional")
        version_label.setStyleSheet("""
            color: #ecf0f1;
            font-size: 14px;
            font-weight: 600;
            margin: 0;
            padding: 0;
        """)
        
        status_label = QLabel("Ready for scraping")
        status_label.setStyleSheet("""
            color: #2ecc71;
            font-size: 12px;
            font-weight: 500;
            margin: 0;
            padding: 0;
        """)
        
        right_layout.addWidget(version_label)
        right_layout.addWidget(status_label)
        
        header_layout.addLayout(left_layout)
        header_layout.addStretch()
        header_layout.addLayout(right_layout)
        
        layout.addWidget(header_frame)
        
    def create_scraper_tab(self):
        """Create the main scraper interface tab"""
        scraper_widget = QWidget()
        layout = QVBoxLayout(scraper_widget)
        layout.setSpacing(20)
        
        # Control panel
        control_group = QGroupBox("🎯 Scraping Controls")
        control_layout = QGridLayout(control_group)
        control_layout.setSpacing(15)
        control_layout.setContentsMargins(20, 25, 20, 20)
        
        # Source selection
        source_label = QLabel("News Sources:")
        source_label.setStyleSheet("font-weight: 600; color: #34495e;")
        control_layout.addWidget(source_label, 0, 0)
        
        self.source_combo = QComboBox()
        self.source_combo.addItem("All Sources")
        for source in self.news_sources:
            self.source_combo.addItem(source.name)
        control_layout.addWidget(self.source_combo, 0, 1)
        
        # Max headlines
        headlines_label = QLabel("Max Headlines per Source:")
        headlines_label.setStyleSheet("font-weight: 600; color: #34495e;")
        control_layout.addWidget(headlines_label, 1, 0)
        
        self.max_headlines_spin = QSpinBox()
        self.max_headlines_spin.setRange(10, 200)
        self.max_headlines_spin.setValue(50)
        control_layout.addWidget(self.max_headlines_spin, 1, 1)
        
        # Custom URL input
        custom_label = QLabel("Custom URL:")
        custom_label.setStyleSheet("font-weight: 600; color: #34495e;")
        control_layout.addWidget(custom_label, 2, 0)
        
        self.custom_url_input = QLineEdit()
        self.custom_url_input.setPlaceholderText("Enter custom news website URL (optional)...")
        control_layout.addWidget(self.custom_url_input, 2, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.scrape_btn = QPushButton("🚀 Start Scraping")
        self.scrape_btn.setObjectName("success")
        self.scrape_btn.clicked.connect(self.start_scraping)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self.stop_scraping)
        self.stop_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("🗑️ Clear Results")
        self.clear_btn.setObjectName("warning")
        self.clear_btn.clicked.connect(self.clear_results)
        
        button_layout.addWidget(self.scrape_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        control_layout.addLayout(button_layout, 3, 0, 1, 2)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #ecf0f1;
                border: 2px solid #dee2e6;
                border-radius: 12px;
                height: 30px;
                text-align: center;
                color: #2c3e50;
                font-weight: 600;
                font-size: 13px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 10px;
            }
        """)
        control_layout.addWidget(self.progress_bar, 4, 0, 1, 2)
        
        layout.addWidget(control_group)
        
        # Live results preview
        preview_group = QGroupBox("📡 Live Results Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(20, 25, 20, 20)
        
        self.live_results = QTextEdit()
        self.live_results.setMaximumHeight(200)
        self.live_results.setReadOnly(True)
        self.live_results.setPlaceholderText("Live headlines will appear here during scraping...")
        self.live_results.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 15px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        preview_layout.addWidget(self.live_results)
        
        layout.addWidget(preview_group)
        
        self.tab_widget.addTab(scraper_widget, "📡 Scraper")
        
    def create_results_tab(self):
        """Create results display tab"""
        results_widget = QWidget()
        layout = QVBoxLayout(results_widget)
        layout.setSpacing(20)
        
        # Export controls
        export_group = QGroupBox("💾 Export Options")
        export_layout = QHBoxLayout(export_group)
        export_layout.setContentsMargins(20, 25, 20, 20)
        export_layout.setSpacing(15)
        
        self.export_txt_btn = QPushButton("📄 Export to TXT")
        self.export_txt_btn.clicked.connect(self.export_to_txt)
        
        self.export_csv_btn = QPushButton("📊 Export to CSV")
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        
        self.export_json_btn = QPushButton("📋 Export to JSON")
        self.export_json_btn.clicked.connect(self.export_to_json)
        
        export_layout.addWidget(self.export_txt_btn)
        export_layout.addWidget(self.export_csv_btn)
        export_layout.addWidget(self.export_json_btn)
        export_layout.addStretch()
        
        layout.addWidget(export_group)
        
        # Results table
        results_group = QGroupBox("📋 Headlines Results")
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(20, 25, 20, 20)
        
        # Results info
        self.results_info = QLabel("No headlines scraped yet. Use the Scraper tab to get started.")
        self.results_info.setStyleSheet("""
            color: #7f8c8d;
            font-size: 12px;
            font-style: italic;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        """)
        results_layout.addWidget(self.results_info)
        
        self.results_table = ModernTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["📰 Title", "🏢 Source", "🕒 Timestamp", "🔗 URL"])
        
        # Set column widths
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Enable sorting and selection
        self.results_table.setSortingEnabled(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        
        # Double-click to open URL
        self.results_table.cellDoubleClicked.connect(self.open_url)
        
        results_layout.addWidget(self.results_table)
        layout.addWidget(results_group)
        
        self.tab_widget.addTab(results_widget, "📊 Results")
        
    def create_settings_tab(self):
        """Create settings configuration tab"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        layout.setSpacing(20)
        
        # Auto-refresh settings
        refresh_group = QGroupBox("🔄 Auto-Refresh Settings")
        refresh_layout = QGridLayout(refresh_group)
        refresh_layout.setContentsMargins(0, 0, 0, 0)
        refresh_layout.setSpacing(0)
        
        self.auto_refresh_check = QCheckBox("Enable Auto-Refresh")
        refresh_layout.addWidget(self.auto_refresh_check, 0, 0, 1, 1)
        
        interval_label = QLabel("Refresh Interval (minutes):")
        interval_label.setStyleSheet("font-weight: 600; color: #34495e;")
        refresh_layout.addWidget(interval_label, 1, 0)
        
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1, 1440)  # 1 minute to 24 hours
        self.refresh_interval_spin.setValue(30)
        refresh_layout.addWidget(self.refresh_interval_spin, 1, 10)
        
        layout.addWidget(refresh_group)
        
        # Data management
        data_group = QGroupBox("💾 Data Management")
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(0, 0, 0, 0)
        
        self.auto_save_check = QCheckBox("Auto-save results after scraping")

        data_layout.addWidget(self.auto_save_check)
        
        layout.addWidget(data_group)
        
        # Advanced settings
        advanced_group = QGroupBox("⚙️ Advanced Settings")
        advanced_layout = QGridLayout(advanced_group)
        advanced_layout.setContentsMargins(0, 0, 0, 0)   #20, 25, 20, 20
        advanced_layout.setSpacing(0)  #15
        
        timeout_label = QLabel("Request Timeout (seconds):")
        timeout_label.setStyleSheet("font-weight: 600; color: black; padding: 1px; background-color: white ;")
        advanced_layout.addWidget(timeout_label, 0, 0)

        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 10)
        self.timeout_spin.setValue(1) #10
        advanced_layout.addWidget(self.timeout_spin, 0, 1)
        
        delay_label = QLabel("Delay between requests (seconds):")
        delay_label.setStyleSheet("font-weight: 600; color: white; padding: 1px; background-color: white;")
        advanced_layout.addWidget(delay_label, 1, 0) #11
        
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10) #10
        self.delay_spin.setValue(1)
        advanced_layout.addWidget(self.delay_spin, 1, 1)
        
        layout.addWidget(advanced_group)
        
        # Troubleshooting group
        troubleshooting_group = QGroupBox("🔧 Troubleshooting Tools")
        troubleshooting_layout = QVBoxLayout(troubleshooting_group)
        troubleshooting_layout.setContentsMargins(0,0,0,0)  #20, 25, 20, 20
        troubleshooting_layout.setSpacing(0)

        
        # Test URL section
        test_section = QFrame()
        test_section.setStyleSheet("""
            QFrame {
                background-color: #f0f8ff;
                
                
                padding: 0px;
                width: 100%;
                length: 100%;
                                   
            }
        """)
        test_layout = QVBoxLayout(test_section)
        
        test_url_layout = QHBoxLayout()
        test_url_label = QLabel("Test URL:")
        test_url_label.setStyleSheet("font-weight: 600; color: #34495e; min-width: 40px; padding: 1px; ")
        
        self.test_url_input = QLineEdit()
        self.test_url_input.setPlaceholderText("Enter URL to test (e.g., https://indianexpress.com/section/india/)")
        
        self.test_url_btn = QPushButton("🧪 Test URL")
        self.test_url_btn.clicked.connect(self.test_single_url)
        
        
        test_url_layout.addWidget(test_url_label)
        test_url_layout.addWidget(self.test_url_input, 1)
        test_url_layout.addWidget(self.test_url_btn)
        
        # Test results
        results_label = QLabel("Test Results:")
        results_label.setStyleSheet("font-weight: 600; color: #34495e; margin-top: 10px;")
        
        self.test_results = QTextEdit()
        self.test_results.setMaximumHeight(150)
        self.test_results.setReadOnly(True)
        self.test_results.setPlaceholderText("Test results will appear here...")
        self.test_results.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #2c3e50;
                border: 2px solid #dee2e6;
                border-radius: 6px;
                padding: 2px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        
        test_layout.addLayout(test_url_layout)
        test_layout.addWidget(results_label)
        test_layout.addWidget(self.test_results)
        
        troubleshooting_layout.addWidget(test_section)
        
        # Tips section
        tips_section = QFrame()
        tips_section.setStyleSheet("""
            QFrame {
                background-color: #e8f4fd;
                border: 1px solid #3498db;
                border-radius: 8px;
                padding: 2px;
            }
        """)
        tips_layout = QVBoxLayout(tips_section)
        
        tips_title = QLabel("💡 Common Issues & Solutions")
        tips_title.setStyleSheet("font-weight: 600; color: #2980b9; font-size: 14px; margin-bottom: 10px; padding-left: 2px;")
        
        tips_text = QLabel("""
        • <b>403 Forbidden:</b> Website blocks bots - try VPN or different browser headers<br>
        • <b>Empty Results:</b> Check CSS selectors or website structure changes<br>
        • <b>Timeout Errors:</b> Website is slow - increase timeout in Advanced Settings<br>
        • <b>Indian Express Issues:</b> Use RSS feed: https://indianexpress.com/section/india/feed/<br>
        • <b>Rate Limiting:</b> Increase delay between requests to avoid being blocked
        """)
        tips_text.setWordWrap(True)
        tips_text.setStyleSheet("""
            color: #2c3e50; 
            font-size: 12px; 
            line-height: 1.5;
            background-color: #ffffff;
        """)
        
        tips_layout.addWidget(tips_title)
        tips_layout.addWidget(tips_text)
        
        troubleshooting_layout.addWidget(tips_section)
        
        layout.addWidget(troubleshooting_group)
        
        # Save settings button
        save_settings_btn = QPushButton("💾 Save Settings")
        save_settings_btn.setObjectName("success")
        save_settings_btn.clicked.connect(self.save_settings)
        save_settings_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: 600;
                padding: 12px 30px;
                margin: 10px 0;
            }
        """)
        layout.addWidget(save_settings_btn)
        
        layout.addStretch()
        
        self.tab_widget.addTab(settings_widget, "⚙️ Settings")
        
    def create_analytics_tab(self):
        """Create analytics and statistics tab"""
        analytics_widget = QWidget()
        layout = QVBoxLayout(analytics_widget)
        layout.setSpacing(20)
        
        # Statistics group
        stats_group = QGroupBox("📈 Scraping Statistics")
        stats_layout = QGridLayout(stats_group)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(0)
        
        # Create stat cards
        self.create_stat_card(stats_layout, "total_headlines", "📰", "Total Headlines", "0", 0, 0)
        self.create_stat_card(stats_layout, "unique_sources", "🏢", "Unique Sources", "0", 0, 1)
        self.create_stat_card(stats_layout, "last_scrape", "🕒", "Last Scrape", "Never", 1, 0)
        self.create_stat_card(stats_layout, "success_rate", "✅", "Success Rate", "0%", 1, 1)
        
        layout.addWidget(stats_group)
        
        # Source breakdown
        breakdown_group = QGroupBox("📊 Source Breakdown")
        breakdown_layout = QVBoxLayout(breakdown_group)
        breakdown_layout.setContentsMargins(0, 0, 0, 0)
        
        self.source_tree = QTreeWidget()
        self.source_tree.setHeaderLabels(["📰 Source", "📊 Headlines Count", "🕒 Last Updated"])
        self.source_tree.setRootIsDecorated(False)
        self.source_tree.setAlternatingRowColors(True)
        breakdown_layout.addWidget(self.source_tree)
        
        layout.addWidget(breakdown_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(analytics_widget, "📈 Analytics")
        
    def create_stat_card(self, layout, attr_name, icon, title, value, row, col):
        """Create a statistics card widget"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 15px;
                color: black;
            }
            QFrame:hover {
                border-color: #3498db;
                transform: translateY(-2px);
            }
        """)
        card.setFixedHeight(120)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        
        # Icon and title row
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px; color: #3498db;")
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #7f8c8d;")
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: 700; 
            color: #2c3e50; 
            margin-top: 5px;
        """)
        
        # Store reference to update later
        setattr(self, f"{attr_name}_label", value_label)
        
        card_layout.addLayout(header_layout)
        card_layout.addWidget(value_label)
        card_layout.addStretch()
        
        layout.addWidget(card, row, col)
        
    def create_status_bar(self):
        """Create status bar with information"""
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready to scrape news headlines...")
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #ffffff;
                color: #2c3e50;
                border-top: 2px solid #dee2e6;
                font-size: 12px;
                font-weight: 500;
                padding: 8px 15px;
            }
        """)
        self.setStatusBar(self.status_bar)
        
    def start_scraping(self):
        """Start the scraping process"""
        if self.scraper_thread and self.scraper_thread.isRunning():
            return
            
        # Determine which sources to scrape
        selected_sources = []
        if self.source_combo.currentText() == "All Sources":
            selected_sources = self.news_sources
        else:
            source_name = self.source_combo.currentText()
            selected_sources = [s for s in self.news_sources if s.name == source_name]
        
        # Add custom URL if provided
        custom_url = self.custom_url_input.text().strip()
        if custom_url:
            custom_source = NewsSource("Custom URL", custom_url, 
                                     ["h1", "h2", "h3", ".headline", ".title", "article h2", "article h3"])
            selected_sources.append(custom_source)
        
        if not selected_sources:
            QMessageBox.warning(self, "Warning", "No sources selected!")
            return
            
        # Clear live results
        self.live_results.clear()
        self.live_results.append("🚀 Starting scraping process...\n")
        
        # Setup UI for scraping
        self.scrape_btn.setEnabled(False)
        self.scrape_btn.setText("🔄 Scraping...")
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start scraping thread
        max_headlines = self.max_headlines_spin.value()
        self.scraper_thread = ScraperThread(selected_sources, max_headlines)
        
        # Connect signals
        self.scraper_thread.progress_update.connect(self.progress_bar.setValue)
        self.scraper_thread.headline_found.connect(self.add_headline_live)
        self.scraper_thread.finished_scraping.connect(self.scraping_finished)
        self.scraper_thread.error_occurred.connect(self.show_error)
        
        self.scraper_thread.start()
        self.status_bar.showMessage("🔄 Scraping in progress...")
        
    def stop_scraping(self):
        """Stop the scraping process"""
        if self.scraper_thread:
            self.scraper_thread.stop()
            self.scraper_thread.wait()
            
        self.scrape_btn.setEnabled(True)
        self.scrape_btn.setText("🚀 Start Scraping")
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("⏹️ Scraping stopped by user")
        
    def add_headline_live(self, headline):
        """Add headline to live results preview with better formatting"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_text = f"[{timestamp}] 🏢 {headline['source']}\n📰 {headline['title']}\n{'─' * 50}\n"
        self.live_results.append(formatted_text)
        
        # Auto-scroll to bottom
        cursor = self.live_results.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.live_results.setTextCursor(cursor)
        
    def scraping_finished(self, headlines):
        """Handle scraping completion"""
        self.headlines.extend(headlines)
        
        # Reset UI
        self.scrape_btn.setEnabled(True)
        self.scrape_btn.setText("🚀 Start Scraping")
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # Update results table
        self.update_results_table()
        
        # Update analytics
        self.update_analytics()
        
        # Show completion message
        message = f"✅ Scraping completed! Found {len(headlines)} new headlines."
        self.status_bar.showMessage(message)
        
        # Update live results
        self.live_results.append(f"\n🎉 {message}")
        
        # Auto-save if enabled
        if hasattr(self, 'auto_save_check') and self.auto_save_check.isChecked():
            self.export_to_txt(auto_save=True)
            
    def update_results_table(self):
        """Update the results table with current headlines"""
        self.results_table.setRowCount(len(self.headlines))
        
        for row, headline in enumerate(self.headlines):
            # Title
            title_item = QTableWidgetItem(headline['title'])
            title_item.setToolTip(headline['title'])  # Show full title on hover
            self.results_table.setItem(row, 0, title_item)
            
            # Source
            source_item = QTableWidgetItem(headline['source'])
            self.results_table.setItem(row, 1, source_item)
            
            # Timestamp
            timestamp_item = QTableWidgetItem(headline['timestamp'])
            self.results_table.setItem(row, 2, timestamp_item)
            
            # URL
            url_item = QTableWidgetItem(headline['url'])
            url_item.setToolTip("Double-click to open in browser")
            self.results_table.setItem(row, 3, url_item)
        
        # Update results info
        total_headlines = len(self.headlines)
        unique_sources = len(set(h['source'] for h in self.headlines))
        
        if total_headlines > 0:
            self.results_info.setText(
                f"📊 Showing {total_headlines} headlines from {unique_sources} sources. "
                f"Double-click any row to open the article in your browser."
            )
            self.results_info.setStyleSheet("""
                color: #27ae60;
                font-size: 12px;
                font-weight: 500;
                padding: 10px;
                background-color: #d5f4e6;
                border-radius: 6px;
                border-left: 4px solid #27ae60;
            """)
        
    def update_analytics(self):
        """Update analytics display with better formatting"""
        if not hasattr(self, 'total_headlines_label'):
            return
            
        total_headlines = len(self.headlines)
        unique_sources = len(set(h['source'] for h in self.headlines))
        last_scrape = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if self.headlines else "Never"
        
        # Calculate success rate (dummy calculation for now)
        success_rate = min(100, (total_headlines / 10) * 10) if total_headlines > 0 else 0
        
        self.total_headlines_label.setText(f"{total_headlines:,}")
        self.unique_sources_label.setText(f"{unique_sources}")
        self.last_scrape_label.setText(last_scrape)
        self.success_rate_label.setText(f"{success_rate:.0f}%")
        
        # Update source tree
        self.source_tree.clear()
        source_counts = {}
        for headline in self.headlines:
            source = headline['source']
            if source not in source_counts:
                source_counts[source] = {'count': 0, 'last_updated': headline['timestamp']}
            source_counts[source]['count'] += 1
            if headline['timestamp'] > source_counts[source]['last_updated']:
                source_counts[source]['last_updated'] = headline['timestamp']
        
        # Sort by count (descending)
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1]['count'], reverse=True)
        
        for source, data in sorted_sources:
            item = QTreeWidgetItem([source, f"{data['count']:,}", data['last_updated']])
            self.source_tree.addTopLevelItem(item)
        
        # Resize columns to content
        self.source_tree.resizeColumnToContents(0)
        self.source_tree.resizeColumnToContents(1)
        self.source_tree.resizeColumnToContents(2)
            
    def clear_results(self):
        """Clear all results with confirmation"""
        if not self.headlines:
            QMessageBox.information(self, "Info", "No results to clear!")
            return
            
        reply = QMessageBox.question(self, "Confirm Clear", 
                                   f"Are you sure you want to clear all {len(self.headlines)} results?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.headlines.clear()
            self.results_table.setRowCount(0)
            self.live_results.clear()
            self.update_analytics()
            
            # Reset results info
            self.results_info.setText("No headlines scraped yet. Use the Scraper tab to get started.")
            self.results_info.setStyleSheet("""
                color: #7f8c8d;
                font-size: 12px;
                font-style: italic;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 6px;
                border-left: 4px solid #3498db;
            """)
            
            self.status_bar.showMessage("🗑️ Results cleared successfully")
            
    def export_to_txt(self, auto_save=False):
        """Export headlines to text file"""
        if not self.headlines:
            QMessageBox.information(self, "Info", "No headlines to export!")
            return
            
        if auto_save:
            filename = f"headlines_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(os.getcwd(), filename)
        else:
            filepath, _ = QFileDialog.getSaveFileName(
                self, "Save Headlines", f"headlines_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Text Files (*.txt)")
            
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("=" * 80 + "\n")
                    f.write("PROFESSIONAL NEWS HEADLINES SCRAPER - EXPORT REPORT\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total Headlines: {len(self.headlines)}\n")
                    f.write(f"Unique Sources: {len(set(h['source'] for h in self.headlines))}\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for i, headline in enumerate(self.headlines, 1):
                        f.write(f"[{i:03d}] {headline['title']}\n")
                        f.write(f"      Source: {headline['source']}\n")
                        f.write(f"      Time: {headline['timestamp']}\n")
                        f.write(f"      URL: {headline['url']}\n")
                        f.write("-" * 80 + "\n\n")
                
                if not auto_save:
                    QMessageBox.information(self, "Success", f"📄 Headlines exported to {filepath}")
                self.status_bar.showMessage(f"📄 Exported {len(self.headlines)} headlines to TXT")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")
                
    def export_to_csv(self):
        """Export headlines to CSV file"""
        if not self.headlines:
            QMessageBox.information(self, "Info", "No headlines to export!")
            return
            
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Headlines CSV", f"headlines_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)")
            
        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Title', 'Source', 'Timestamp', 'URL'])
                    
                    for headline in self.headlines:
                        writer.writerow([
                            headline['title'],
                            headline['source'],
                            headline['timestamp'],
                            headline['url']
                        ])
                
                QMessageBox.information(self, "Success", f"📊 Headlines exported to {filepath}")
                self.status_bar.showMessage(f"📊 Exported {len(self.headlines)} headlines to CSV")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")
                
    def export_to_json(self):
        """Export headlines to JSON file"""
        if not self.headlines:
            QMessageBox.information(self, "Info", "No headlines to export!")
            return
            
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Headlines JSON", f"headlines_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)")
            
        if filepath:
            try:
                export_data = {
                    'export_info': {
                        'application': 'Professional News Headlines Scraper v2.0',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'total_headlines': len(self.headlines),
                        'unique_sources': list(set(h['source'] for h in self.headlines)),
                        'source_counts': {}
                    },
                    'headlines': self.headlines
                }
                
                # Add source counts
                for headline in self.headlines:
                    source = headline['source']
                    export_data['export_info']['source_counts'][source] = \
                        export_data['export_info']['source_counts'].get(source, 0) + 1
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "Success", f"📋 Headlines exported to {filepath}")
                self.status_bar.showMessage(f"📋 Exported {len(self.headlines)} headlines to JSON")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export JSON: {str(e)}")
                
    def open_url(self, row, column):
        """Open URL when table cell is double-clicked"""
        url = self.results_table.item(row, 3).text()  # URL is in column 3
        if url and url.startswith('http'):
            try:
                webbrowser.open(url)
                self.status_bar.showMessage(f"🌐 Opened article in browser: {url}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to open URL: {str(e)}")
        else:
            QMessageBox.information(self, "Info", "Invalid or missing URL")
                
    def show_error(self, error_message):
        """Show error message with better formatting"""
        # Create custom message box
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Scraping Error")
        msg.setText("An error occurred during scraping:")
        msg.setDetailedText(error_message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Apply custom styling
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
                color: #2c3e50;
            }
            QMessageBox QPushButton {
                background-color: #e74c3c;
                color: #ffffff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: 600;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        msg.exec()
        self.status_bar.showMessage(f"❌ Error: {error_message}")
        
    def save_settings(self):
        """Save application settings"""
        try:
            self.settings.setValue('auto_refresh_enabled', self.auto_refresh_check.isChecked())
            self.settings.setValue('refresh_interval', self.refresh_interval_spin.value())
            self.settings.setValue('auto_save_enabled', self.auto_save_check.isChecked())
            self.settings.setValue('request_timeout', self.timeout_spin.value())
            self.settings.setValue('request_delay', self.delay_spin.value())
            self.settings.setValue('max_headlines', self.max_headlines_spin.value())
            
            # Setup auto-refresh timer
            if self.auto_refresh_check.isChecked():
                interval_ms = self.refresh_interval_spin.value() * 60 * 1000  # Convert to milliseconds
                self.auto_refresh_timer.start(interval_ms)
                refresh_status = f"Auto-refresh enabled ({self.refresh_interval_spin.value()} min intervals)"
            else:
                self.auto_refresh_timer.stop()
                refresh_status = "Auto-refresh disabled"
                
            QMessageBox.information(self, "Settings Saved", 
                                  f"✅ Settings saved successfully!\n\n{refresh_status}")
            self.status_bar.showMessage("💾 Settings saved successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
        
    def load_settings(self):
        """Load saved settings"""
        try:
            if hasattr(self, 'auto_refresh_check'):
                self.auto_refresh_check.setChecked(
                    self.settings.value('auto_refresh_enabled', False, type=bool))
                self.refresh_interval_spin.setValue(
                    self.settings.value('refresh_interval', 30, type=int))
                self.auto_save_check.setChecked(
                    self.settings.value('auto_save_enabled', False, type=bool))
                self.timeout_spin.setValue(
                    self.settings.value('request_timeout', 10, type=int))
                self.delay_spin.setValue(
                    self.settings.value('request_delay', 1, type=int))
                self.max_headlines_spin.setValue(
                    self.settings.value('max_headlines', 50, type=int))
        except Exception as e:
            print(f"Error loading settings: {e}")
                
    def test_single_url(self):
        """Test a single URL to diagnose scraping issues"""
        url = self.test_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL to test!")
            return
            
        if not url.startswith('http'):
            url = 'https://' + url
            
        self.test_results.clear()
        self.test_results.append(f"🧪 Testing URL: {url}\n")
        self.test_results.append("=" * 50 + "\n")
        
        # Disable button during test
        self.test_url_btn.setEnabled(False)
        self.test_url_btn.setText("🔄 Testing...")
        
        # Run test in background
        def run_test():
            try:
                # Test with enhanced headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                self.test_results.append("📡 Sending request with browser headers...")
                QApplication.processEvents()
                
                response = requests.get(url, headers=headers, timeout=15)
                
                self.test_results.append(f"📊 Response Status: {response.status_code}")
                self.test_results.append(f"📏 Content Length: {len(response.content):,} bytes")
                
                if response.status_code == 200:
                    # Parse content
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Try different selectors
                    selectors_to_try = [
                        'h1', 'h2', 'h3', 'h4',
                        '.title a', '.headline', '.story-title',
                        'a[href*="news"]', 'a[href*="story"]',
                        '.ie-custom-story-item h3 a',  # Indian Express specific
                        '.story-details h3 a'  # Indian Express specific
                    ]
                    
                    found_elements = {}
                    for selector in selectors_to_try:
                        try:
                            elements = soup.select(selector)
                            if elements:
                                found_elements[selector] = len(elements)
                        except Exception as e:
                            continue
                    
                    if found_elements:
                        self.test_results.append("\n✅ Found potential headline selectors:")
                        for selector, count in sorted(found_elements.items(), key=lambda x: x[1], reverse=True):
                            self.test_results.append(f"   🎯 '{selector}': {count} elements")
                            
                        # Show sample headlines
                        best_selector = max(found_elements.items(), key=lambda x: x[1])[0]
                        sample_elements = soup.select(best_selector)[:3]
                        
                        self.test_results.append(f"\n📰 Sample headlines using '{best_selector}':")
                        for i, elem in enumerate(sample_elements):
                            title = elem.get_text().strip()[:100]
                            if title:
                                self.test_results.append(f"   {i+1}. {title}...")
                                
                    else:
                        self.test_results.append("\n❌ No headline elements found with common selectors")
                        self.test_results.append("💡 Try adding custom CSS selectors for this site")
                        
                elif response.status_code == 403:
                    self.test_results.append("\n🚫 403 Forbidden - Website is blocking automated requests")
                    self.test_results.append("\n💡 Possible Solutions:")
                    self.test_results.append("   • Try using a VPN service")
                    self.test_results.append("   • Use RSS feed if available")
                    self.test_results.append("   • Contact website for API access")
                    self.test_results.append("   • Try different user agent strings")
                    
                    # Check for RSS feed
                    try:
                        rss_urls = [
                            url.rstrip('/') + '/feed/',
                            url.rstrip('/') + '/rss/',
                            url.rstrip('/') + '/rss.xml'
                        ]
                        
                        for rss_url in rss_urls:
                            try:
                                rss_response = requests.get(rss_url, headers=headers, timeout=5)
                                if rss_response.status_code == 200 and 'xml' in rss_response.headers.get('content-type', ''):
                                    self.test_results.append(f"   📡 RSS feed found: {rss_url}")
                                    break
                            except:
                                continue
                    except:
                        pass
                        
                elif response.status_code == 429:
                    self.test_results.append("\n⏳ 429 Too Many Requests - Rate limited")
                    self.test_results.append("💡 Increase delay between requests in Advanced Settings")
                    
                else:
                    self.test_results.append(f"\n❓ Unexpected status code: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                self.test_results.append("\n⏰ Request timeout - Website is slow or unreachable")
                self.test_results.append("💡 Try increasing timeout in Advanced Settings")
                
            except requests.exceptions.ConnectionError:
                self.test_results.append("\n🌐 Connection error - Check internet connection")
                self.test_results.append("💡 Verify the URL is correct and accessible")
                
            except Exception as e:
                self.test_results.append(f"\n❌ Unexpected error: {str(e)}")
                
            finally:
                # Re-enable button
                QApplication.processEvents()
                self.test_url_btn.setEnabled(True)
                self.test_url_btn.setText("🧪 Test URL")
                self.test_results.append(f"\n{'=' * 50}")
                self.test_results.append("🏁 Test completed")
        
        # Run in background thread
        test_thread = threading.Thread(target=run_test)
        test_thread.daemon = True
        test_thread.start()
                
    def closeEvent(self, event):
        """Handle application close event"""
        # Stop scraping thread if running
        if self.scraper_thread and self.scraper_thread.isRunning():
            reply = QMessageBox.question(self, "Confirm Exit", 
                                       "Scraping is in progress. Do you want to exit anyway?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            else:
                self.scraper_thread.stop()
                self.scraper_thread.wait()
        
        # Save window geometry
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('window_state', self.saveState())
        
        event.accept()


class SplashScreen(QWidget):
    """Custom splash screen for application startup"""
    
    def __init__(self):
        super().__init__()
        self.setFixedSize(450, 350)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # Center the splash screen
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)
        
        # Setup UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Background with gradient
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c3e50, stop:0.5 #34495e, stop:1 #3498db);
                border-radius: 20px;
                color: #ffffff;
            }
        """)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(50, 50, 50, 50)
        content_layout.setSpacing(20)
        
        # Logo/Icon
        icon_label = QLabel("📰")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("""
            font-size: 64px; 
            color: #ffffff; 
            margin-bottom: 10px;
            background: transparent;
        """)
        
        # Title
        title_label = QLabel("NewsVision")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            color: #ffffff; 
            font-size: 22px; 
            font-weight: 700; 
            margin-bottom: 5px;
            background: transparent;
        """)
        
        # Subtitle
        subtitle_label = QLabel("Advanced Web Scraping Tool")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            color: #bdc3c7; 
            font-size: 14px; 
            font-weight: 400; 
            margin-bottom: 10px;
            background: transparent;
        """)
        
        # Version
        version_label = QLabel("Version 2.0 Professional")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("""
            color: #ecf0f1; 
            font-size: 12px; 
            margin-bottom: 20px;
            background: transparent;
        """)
        
        # Loading text
        self.loading_label = QLabel("Initializing application...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("""
            color: #ffffff; 
            font-size: 12px; 
            margin-bottom: 10px;
            background: transparent;
        """)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate progress
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: rgba(255, 255, 255, 0.2);
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 3px;
            }
        """)
        
        content_layout.addWidget(icon_label)
        content_layout.addWidget(title_label)
        content_layout.addWidget(subtitle_label)
        content_layout.addWidget(version_label)
        content_layout.addStretch()
        content_layout.addWidget(self.loading_label)
        content_layout.addWidget(self.progress)
        
        layout.addLayout(content_layout)
        
        # Timer for splash screen
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(800)
        
        self.step = 0
        self.steps = [
            "Initializing components...",
            "Loading news sources...",
            "Setting up interface...",
            "Applying professional theme...",
            "Ready to launch!"
        ]
        
    def update_progress(self):
        """Update splash screen progress"""
        if self.step < len(self.steps):
            self.loading_label.setText(self.steps[self.step])
            self.step += 1
        else:
            self.timer.stop()
            self.close()


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("NewsVision")
    app.setApplicationVersion("2.0 Professional")
    app.setOrganizationName("NewsScraperApp")
    app.setApplicationDisplayName("NewsVision v2.0")
    
    # Show splash screen
    splash = SplashScreen()
    splash.show()
    
    # Process events to show splash
    app.processEvents()
    
    # Small delay to show splash
    import time
    time.sleep(3)  # Longer delay to appreciate the professional splash
    
    # Create main window
    window = NewsScraperApp()
    
    # Close splash and show main window
    splash.close()
    window.show()
    
    # Restore window geometry if saved
    geometry = window.settings.value('geometry')
    if geometry:
        window.restoreGeometry(geometry)
        
    window_state = window.settings.value('window_state')
    if window_state:
        window.restoreState(window_state)
    
    # Ensure window is visible and properly sized
    window.raise_()
    window.activateWindow()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()