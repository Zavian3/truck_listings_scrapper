#!/usr/bin/env python3
"""
Unified Truck Listing Scraper - Streamlit App
Combines Craigslist and Facebook Marketplace scraping with Google Sheets integration
"""

import streamlit as st
import time
import json
import re
import os
import pickle
from datetime import datetime
import pandas as pd
from urllib.parse import urljoin, urlparse
import gspread
from google.oauth2 import service_account

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class GoogleSheetsManager:
    def __init__(self, service_account_file="service_account.json"):
        """Initialize Google Sheets manager with service account"""
        self.service_account_file = service_account_file
        self.client = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        try:
            # Define the scope for Google Sheets and Drive API
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = None
            
            # Try Streamlit secrets first (for cloud deployment)
            try:
                if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
                    credentials = service_account.Credentials.from_service_account_info(
                        st.secrets["google_service_account"], scopes=scopes
                    )
                    st.success("Using Streamlit Cloud secrets for authentication")
            except Exception as e:
                st.info(f"Streamlit secrets not available: {e}")
            
            # Fallback to local file
            if credentials is None:
                if not os.path.exists(self.service_account_file):
                    raise FileNotFoundError(f"Service account file not found: {self.service_account_file}")
                
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=scopes
                )
                st.success("Using local service account file")
            
            self.client = gspread.authorize(credentials)
            return True
            
        except Exception as e:
            st.error(f"Google Sheets authentication failed: {e}")
            st.error("Please ensure you have either:")
            st.error("1. A valid 'service_account.json' file, OR")
            st.error("2. Proper secrets configured in Streamlit Cloud")
            return False
    
    def create_sheet_from_dataframe(self, df, sheet_name, share_with_anyone=True):
        """Create a Google Sheet from DataFrame data"""
        try:
            if df is None or len(df) == 0:
                st.error("No data provided for Google Sheet creation")
                return None, None
            
            st.info(f"Creating sheet with {len(df)} rows of data")
            
            # Clean the data - replace NaN values and handle problematic data
            df = df.fillna('N/A')
            df = df.astype(str)
            
            # Create new spreadsheet
            spreadsheet = self.client.create(sheet_name)
            st.success(f"Created spreadsheet: {sheet_name}")
            
            # Get the first worksheet
            worksheet = spreadsheet.sheet1
            worksheet.clear()
            
            # Upload data to sheet
            data = [df.columns.tolist()] + df.values.tolist()
            worksheet.update(data, value_input_option='RAW')
            st.info(f"Uploaded {len(data)} rows to sheet")
            
            # Format the header row
            self._format_header(worksheet, len(df.columns))
            
            # Share the spreadsheet if requested
            sheet_url = spreadsheet.url
            sharing_success = False
            if share_with_anyone:
                sharing_success = self._share_with_anyone(spreadsheet)
                if sharing_success:
                    st.success("Sheet is now accessible: Anyone with link can VIEW and EDIT")
                else:
                    st.warning("Sharing may have failed - please check sheet permissions manually")
            
            return sheet_url, spreadsheet.id
            
        except Exception as e:
            st.error(f"Failed to create Google Sheet: {e}")
            return None, None
    
    def _format_header(self, worksheet, num_columns):
        """Format the header row with bold text and background color"""
        try:
            header_format = {
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
                "textFormat": {"bold": True},
                "horizontalAlignment": "CENTER"
            }
            worksheet.format(f"1:{1}", header_format)
        except Exception as e:
            st.warning(f"Header formatting failed: {e}")
    
    def _share_with_anyone(self, spreadsheet):
        """Make the spreadsheet editable by anyone with the link"""
        try:
            # Try different sharing methods
            try:
                spreadsheet.share(None, perm_type='anyone', role='editor', notify=False)
                return True
            except:
                try:
                    spreadsheet.share(None, perm_type='anyone', role='writer', notify=False)
                    return True
                except:
                    try:
                        spreadsheet.share('', perm_type='anyone', role='editor')
                        return True
                    except:
                        return False
        except Exception as e:
            st.error(f"Critical sharing error: {e}")
            return False


class CraigslistScraper:
    def __init__(self):
        self.driver = None
        
    def setup_driver(self, headless=True):
        """Set up Chrome driver"""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
            
            # Try local chromedriver first, then system PATH
            driver_path = "./chromedriver"
            service = None
            
            if os.path.exists(driver_path):
                service = Service(driver_path)
            else:
                # Try system PATH (for cloud deployments)
                try:
                    service = Service()  # Will use chromedriver from PATH
                except:
                    st.error("ChromeDriver not found. Please ensure chromedriver is available.")
                    return None
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return self.driver
            
        except Exception as e:
            st.error(f"Failed to setup Chrome driver: {e}")
            st.error("This may be due to missing ChromeDriver or incompatible Chrome version.")
            return None

    def extract_listing_urls(self, search_url):
        """Extract all listing URLs from the search page"""
        st.info(f"Loading Craigslist search page...")
        self.driver.get(search_url)
        
        # Wait for page to load completely
        with st.spinner("Waiting for page to load completely (60 seconds)..."):
            time.sleep(60)
        
        # Additional wait for dynamic content
        try:
            st.info("Waiting for listings to appear...")
            wait = WebDriverWait(self.driver, 30)
            wait.until(lambda driver: 
                      len(driver.find_elements(By.CLASS_NAME, "result-node")) > 0 or
                      len(driver.find_elements(By.CSS_SELECTOR, ".cl-search-result")) > 0 or
                      len(driver.find_elements(By.CSS_SELECTOR, "[data-pid]")) > 0)
            st.success("Listings detected, proceeding with extraction...")
        except:
            st.warning("Timeout waiting for listings, but continuing anyway...")
        
        st.info("Looking for listing URLs...")
        
        listing_urls = []
        try:
            # Look for result-node elements
            result_nodes = self.driver.find_elements(By.CLASS_NAME, "result-node")
            st.info(f"Found {len(result_nodes)} result nodes")
            
            for node in result_nodes:
                try:
                    link_elements = node.find_elements(By.CSS_SELECTOR, "a.cl-app-anchor")
                    for link in link_elements:
                        href = link.get_attribute('href')
                        if href and '/d/' in href:
                            full_url = urljoin(search_url, href)
                            if full_url not in listing_urls:
                                listing_urls.append(full_url)
                                break
                except Exception as e:
                    continue
            
            # Try alternative selectors if no results
            if len(listing_urls) == 0:
                st.info("No result-node elements found, trying alternative selectors...")
                
                search_results = self.driver.find_elements(By.CSS_SELECTOR, ".cl-search-result")
                st.info(f"Found {len(search_results)} cl-search-result elements")
                
                for result in search_results:
                    try:
                        link = result.find_element(By.CSS_SELECTOR, "a")
                        href = link.get_attribute('href')
                        if href and '/d/' in href:
                            full_url = urljoin(search_url, href)
                            if full_url not in listing_urls:
                                listing_urls.append(full_url)
                    except:
                        continue
                
                if len(listing_urls) == 0:
                    pid_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-pid]")
                    st.info(f"Found {len(pid_elements)} elements with data-pid")
                    
                    for element in pid_elements:
                        try:
                            link = element.find_element(By.CSS_SELECTOR, "a")
                            href = link.get_attribute('href')
                            if href and '/d/' in href:
                                full_url = urljoin(search_url, href)
                                if full_url not in listing_urls:
                                    listing_urls.append(full_url)
                        except:
                            continue
            
            st.success(f"Extracted {len(listing_urls)} unique listing URLs")
            return listing_urls
            
        except Exception as e:
            st.error(f"Error finding listing URLs: {e}")
            return []

    def safe_find_element_text(self, selector, method="css"):
        """Safely find element and return text, or empty string if not found"""
        try:
            if method == "css":
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
            elif method == "class":
                element = self.driver.find_element(By.CLASS_NAME, selector)
            elif method == "id":
                element = self.driver.find_element(By.ID, selector)
            elif method == "xpath":
                element = self.driver.find_element(By.XPATH, selector)
            else:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
            
            return element.text.strip()
        except:
            return ''

    def safe_find_element_attribute(self, selector, attribute, method="css"):
        """Safely find element and return attribute value, or empty string if not found"""
        try:
            if method == "css":
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
            elif method == "class":
                element = self.driver.find_element(By.CLASS_NAME, selector)
            elif method == "id":
                element = self.driver.find_element(By.ID, selector)
            elif method == "xpath":
                element = self.driver.find_element(By.XPATH, selector)
            else:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
            
            return element.get_attribute(attribute) or ''
        except:
            return ''

    def extract_listing_details(self, listing_url, index):
        """Extract detailed information from a single listing page"""
        try:
            self.driver.get(listing_url)
            time.sleep(3)
            
            listing_data = {
                'url': listing_url,
                'title': '',
                'price': '',
                'year': '',
                'make': '',
                'model': '',
                'vin': '',
                'mileage': '',
                'cylinders': '',
                'drive': '',
                'fuel': '',
                'color': '',
                'transmission': '',
                'type': '',
                'location': '',
                'google_maps_link': '',
                'date_posted': '',
                'date_scraped': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'Craigslist'
            }
            
            # Extract title
            title = self.safe_find_element_text("#titletextonly", "id")
            if not title:
                title = self.safe_find_element_text(".postingtitletext .titletextonly", "css")
            if not title:
                title = self.safe_find_element_text("h1 .titletextonly", "css")
            if not title:
                title = self.safe_find_element_text(".postingtitle", "css")
            
            if title:
                listing_data['title'] = title
                # Parse make/model from title
                title_match = re.match(r'(\d{4})\s+([A-Za-z]+)\s+([A-Za-z0-9\-\s]+)', title)
                if title_match:
                    listing_data['year'] = title_match.group(1)
                    listing_data['make'] = title_match.group(2)
                    listing_data['model'] = title_match.group(3).strip()
            else:
                url_title = listing_url.split('/')[-1].replace('.html', '').replace('-', ' ').title()
                listing_data['title'] = url_title
            
            # Extract other details
            listing_data['price'] = self.safe_find_element_text(".price", "css")
            listing_data['vin'] = self.safe_find_element_text(".attr.auto_vin .valu", "css")
            listing_data['mileage'] = self.safe_find_element_text(".attr.auto_miles .valu", "css")
            listing_data['cylinders'] = self.safe_find_element_text(".attr.auto_cylinders .valu", "css")
            listing_data['drive'] = self.safe_find_element_text(".attr.auto_drivetrain .valu", "css")
            listing_data['fuel'] = self.safe_find_element_text(".attr.auto_fuel_type .valu", "css")
            listing_data['color'] = self.safe_find_element_text(".attr.auto_paint .valu", "css")
            listing_data['transmission'] = self.safe_find_element_text(".attr.auto_transmission .valu", "css")
            listing_data['type'] = self.safe_find_element_text(".attr.auto_bodytype .valu", "css")
            
            # Extract location
            location_parts = []
            primary_location = self.safe_find_element_text(".postingtitletext small", "css")
            if primary_location:
                location_clean = re.sub(r'[()]', '', primary_location).strip()
                location_parts.append(location_clean)
            
            address = self.safe_find_element_text(".mapaddress", "css")
            if address:
                address_clean = re.sub(r'google map.*$', '', address, flags=re.IGNORECASE).strip()
                if address_clean and address_clean not in location_parts:
                    location_parts.append(address_clean)
            
            if location_parts:
                listing_data['location'] = " - ".join(location_parts)
            
            # Extract Google Maps link
            listing_data['google_maps_link'] = self.safe_find_element_attribute(".mapaddress a", "href", "css")
            
            # Extract posting date
            date_posted = self.safe_find_element_attribute("time.date.timeago", "datetime", "css")
            if not date_posted:
                date_posted = self.safe_find_element_attribute("time.date.timeago", "title", "css")
            if not date_posted:
                date_posted = self.safe_find_element_text("time.date.timeago", "css")
            if not date_posted:
                date_posted = self.safe_find_element_text(".postinginfos .postinginfo:first-child .date", "css")
            
            if date_posted:
                listing_data['date_posted'] = date_posted
            
            return listing_data
            
        except Exception as e:
            st.error(f"Error extracting details from {listing_url}: {e}")
            return None

    def scrape_craigslist(self, search_url, max_listings=None):
        """Main Craigslist scraping function"""
        try:
            if not self.setup_driver(headless=True):
                return []
            
            # Step 1: Extract all listing URLs
            listing_urls = self.extract_listing_urls(search_url)
            
            if not listing_urls:
                st.error("No listing URLs found!")
                return []
            
            # Limit listings if specified
            if max_listings and len(listing_urls) > max_listings:
                listing_urls = listing_urls[:max_listings]
                st.info(f"Limited to first {max_listings} listings")
            
            st.info(f"Processing {len(listing_urls)} listings...")
            
            # Step 2: Extract detailed data from each listing
            all_listings = []
            successful_extractions = 0
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, url in enumerate(listing_urls):
                try:
                    status_text.text(f"Processing Craigslist listing {i+1}/{len(listing_urls)}")
                    
                    listing_data = self.extract_listing_details(url, i)
                    
                    if listing_data and (listing_data['title'] or listing_data['price'] or listing_data['vin']):
                        all_listings.append(listing_data)
                        successful_extractions += 1
                        
                        st.success(f"Successfully extracted Craigslist listing {successful_extractions}")
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(listing_urls))
                    
                    # Small delay between requests
                    time.sleep(2)
                    
                except Exception as e:
                    st.error(f"Error processing listing {i+1}: {e}")
                    continue
            
            status_text.text("Craigslist scraping completed!")
            st.success(f"Successfully extracted data from {successful_extractions}/{len(listing_urls)} Craigslist listings")
            
            return all_listings
            
        except Exception as e:
            st.error(f"Error in Craigslist scraping: {e}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()


class FacebookMarketplaceScraper:
    def __init__(self):
        self.driver = None
        self.session_file = "facebook_session.pkl"
        
    def setup_facebook_driver(self, headless=False):
        """Set up Chrome driver with Facebook-specific settings"""
        try:
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument("--headless")
            
            # Facebook-specific settings to avoid detection
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Use a realistic user agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
            
            # Additional privacy settings
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # Faster loading
            
            # Try local chromedriver first, then system PATH
            driver_path = "./chromedriver"
            service = None
            
            if os.path.exists(driver_path):
                service = Service(driver_path)
            else:
                # Try system PATH (for cloud deployments)
                try:
                    service = Service()  # Will use chromedriver from PATH
                except:
                    st.error("ChromeDriver not found. Please ensure chromedriver is available.")
                    return None
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return self.driver
            
        except Exception as e:
            st.error(f"Failed to setup Chrome driver: {e}")
            st.error("This may be due to missing ChromeDriver or incompatible Chrome version.")
            return None

    def save_session(self):
        """Save browser cookies for session persistence"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.session_file, 'wb') as f:
                pickle.dump(cookies, f)
            st.success(f"Session saved to {self.session_file}")
            return True
        except Exception as e:
            st.error(f"Failed to save session: {e}")
            return False

    def load_session(self):
        """Load saved cookies to restore session"""
        try:
            if not os.path.exists(self.session_file):
                st.info(f"No saved session found at {self.session_file}")
                return False
            
            with open(self.session_file, 'rb') as f:
                cookies = pickle.load(f)
            
            # First navigate to Facebook to set the domain context
            self.driver.get("https://www.facebook.com")
            time.sleep(2)
            
            # Load all cookies
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    st.warning(f"Could not add cookie {cookie.get('name', 'unknown')}: {e}")
            
            st.success("Session cookies loaded")
            return True
        except Exception as e:
            st.error(f"Failed to load session: {e}")
            return False

    def get_listing_count(self):
        """Count Facebook Marketplace listings using multiple selector strategies"""
        try:
            # Strategy 1: Look for marketplace item links
            marketplace_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/marketplace/item/']")
            
            # Strategy 2: Look for the specific container structure
            container_selectors = [
                "a[href*='/marketplace/item/']",  # Most reliable
                "[data-testid*='marketplace']",
                "div[data-testid='marketplace-grid'] a",
                "div[role='main'] a[href*='/marketplace/item/']"
            ]
            
            max_count = 0
            for selector in container_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    max_count = max(max_count, len(elements))
                except:
                    continue
            
            return max_count
            
        except Exception as e:
            st.error(f"Error counting listings: {e}")
            return 0

    def wait_and_scroll(self, scroll_attempts=10, scroll_delay=3):
        """Perform infinite scroll to load all listings"""
        st.info(f"Starting Facebook infinite scroll (max {scroll_attempts} attempts)...")
        
        last_count = 0
        no_change_count = 0
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for attempt in range(scroll_attempts):
            # Get current listing count
            current_listings = self.get_listing_count()
            status_text.text(f"Facebook scroll {attempt + 1}: Found {current_listings} listings")
            
            # Check if new listings were loaded
            if current_listings == last_count:
                no_change_count += 1
                if no_change_count >= 3:
                    st.info("No new Facebook listings loaded after 3 attempts, stopping scroll")
                    break
            else:
                no_change_count = 0
            
            last_count = current_listings
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(scroll_delay)
            
            # Try to detect loading indicators
            try:
                loading_elements = self.driver.find_elements(By.CSS_SELECTOR, "[role='progressbar'], [aria-label*='Loading']")
                if loading_elements:
                    st.info("Detected Facebook loading indicator, waiting longer...")
                    time.sleep(5)
            except:
                pass
            
            # Update progress
            progress_bar.progress((attempt + 1) / scroll_attempts)
        
        final_count = self.get_listing_count()
        st.success(f"Facebook infinite scroll complete. Final count: {final_count} listings")
        return final_count

    def extract_all_listings(self):
        """Extract detailed info from all marketplace listings"""
        try:
            st.info("Extracting detailed data from Facebook listings...")
            
            # Find all marketplace listing links
            marketplace_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/marketplace/item/']")
            
            listings = []
            seen_urls = set()  # For duplicate detection
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, link in enumerate(marketplace_links):
                try:
                    status_text.text(f"Processing Facebook listing {i+1}/{len(marketplace_links)}")
                    
                    # Extract URL
                    url = link.get_attribute('href')
                    
                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    listing_data = {
                        'url': url,
                        'title': 'N/A',
                        'price': 'N/A',
                        'mileage': 'N/A',
                        'location': 'N/A'
                    }
                    
                    # Extract price
                    try:
                        # Strategy 1: Look for spans with dir="auto" and Facebook's price classes containing $
                        price_elements = link.find_elements(By.XPATH, ".//span[@dir='auto' and contains(@class, 'x193iq5w') and contains(text(), '$')]")
                        
                        # Strategy 2: Any span with dir="auto" containing $
                        if not price_elements:
                            price_elements = link.find_elements(By.XPATH, ".//span[@dir='auto'][contains(text(), '$')]")
                        
                        # Strategy 3: Any element containing $ symbol
                        if not price_elements:
                            price_elements = link.find_elements(By.XPATH, ".//*[contains(text(), '$')]")
                        
                        for price_elem in price_elements:
                            price_text = price_elem.text.strip()
                            # Check if this looks like a price
                            if '$' in price_text and len(price_text) < 30 and len(price_text) > 1:
                                # Must start with $ and contain digits
                                if price_text.startswith('$') and any(char.isdigit() for char in price_text):
                                    listing_data['price'] = price_text
                                    break
                                    
                    except Exception as e:
                        if i < 5:  # Only show first few errors
                            st.warning(f"Price extraction error for Facebook listing {i+1}: {e}")
                        pass
                    
                    # Extract title from image alt text
                    try:
                        img_elements = link.find_elements(By.TAG_NAME, "img")
                        if img_elements and img_elements[0].get_attribute('alt'):
                            listing_data['title'] = img_elements[0].get_attribute('alt').strip()
                    except:
                        pass
                    
                    # Extract location and mileage
                    try:
                        # Look for location patterns
                        text_elements = link.find_elements(By.XPATH, ".//*[contains(text(), ', ') and (contains(text(), 'OR') or contains(text(), 'WA') or contains(text(), 'CA') or contains(text(), 'ID') or contains(text(), 'NV'))]")
                        for elem in text_elements:
                            text = elem.text.strip()
                            if ', ' in text and len(text) < 50:
                                if 'mile' in text.lower() or 'k mile' in text.lower():
                                    listing_data['mileage'] = text
                                else:
                                    listing_data['location'] = text
                                break
                        
                        # Separate search for mileage if not found above
                        if listing_data['mileage'] == 'N/A':
                            mileage_elements = link.find_elements(By.XPATH, ".//*[contains(text(), 'mile') or contains(text(), 'Mile') or contains(text(), 'K mile')]")
                            for elem in mileage_elements:
                                mileage_text = elem.text.strip()
                                if 'mile' in mileage_text.lower() and len(mileage_text) < 30:
                                    listing_data['mileage'] = mileage_text
                                    break
                    except:
                        pass
                    
                    listings.append(listing_data)
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(marketplace_links))
                    
                except Exception as e:
                    st.warning(f"Error extracting Facebook listing {i+1}: {e}")
                    continue
            
            st.success(f"Extracted {len(listings)} unique Facebook listings")
            return listings
                    
        except Exception as e:
            st.error(f"Error extracting Facebook listings: {e}")
            return []

    def scrape_facebook_marketplace(self, marketplace_url, max_scroll_attempts=15):
        """Main function to scrape Facebook Marketplace listings"""
        try:
            # Check if session exists
            session_exists = os.path.exists(self.session_file)
            headless_success = False
            
            if session_exists:
                st.info("Saved Facebook session found! Trying headless mode...")
                if self.setup_facebook_driver(headless=True):
                    # Try to load saved session
                    st.info("Loading saved Facebook session in headless mode...")
                    session_loaded = self.load_session()
                    
                    if session_loaded:
                        # Test if session works by navigating to marketplace
                        st.info("Testing headless access to Facebook marketplace...")
                        self.driver.get(marketplace_url)
                        time.sleep(10)  # Wait for page load
                        
                        # Check if we can find listings
                        test_count = self.get_listing_count()
                        if test_count > 0:
                            st.success(f"Facebook headless mode successful! Found {test_count} listings")
                            headless_success = True
                        else:
                            st.warning("Facebook headless mode failed - no listings found, switching to visible mode")
                    else:
                        st.warning("Facebook session loading failed, switching to visible mode")
                        
                # Close headless driver if it failed
                if not headless_success and self.driver:
                    self.driver.quit()
                    self.driver = None
            
            # If headless failed or no session, use visible mode
            if not headless_success:
                st.info("Using visible mode for Facebook...")
                
                # Show login instructions
                st.markdown("### 🔐 Facebook Login Required")
                st.markdown("""
                **Steps to complete:**
                1. Click the button below to open Facebook in a new browser window
                2. Log in to Facebook with your credentials
                3. Complete any 2FA if prompted
                4. Make sure you reach Facebook's main page
                5. Come back here and click "Continue Facebook Scraping"
                """)
                
                # Button to open browser
                if st.button("🌐 Open Facebook for Login", type="primary", key="fb_login"):
                    if self.setup_facebook_driver(headless=False):
                        # Try to load saved session first
                        st.info("Attempting to load saved Facebook session...")
                        self.load_session()
                        
                        # Navigate to Facebook
                        st.info("Opening Facebook.com...")
                        self.driver.get("https://www.facebook.com")
                        st.success("Browser opened! Please log in to Facebook, then click 'Continue Facebook Scraping' below.")
                        
                        # Store driver state in session
                        st.session_state.fb_driver_ready = True
                        st.session_state.fb_driver_instance = self.driver
                
                # Continue button (only show if driver is ready)
                if st.session_state.get('fb_driver_ready', False):
                    if st.button("✅ Continue Facebook Scraping (I'm logged in)", type="secondary", key="fb_continue"):
                        # Use the driver from session state
                        if hasattr(st.session_state, 'fb_driver_instance'):
                            self.driver = st.session_state.fb_driver_instance
                            
                            # Save the session for next time
                            st.info("Saving Facebook login session for future runs...")
                            self.save_session()
                            
                            # Navigate to marketplace
                            st.info("Navigating to Facebook marketplace...")
                            self.driver.get(marketplace_url)
                        else:
                            st.error("Driver not found. Please open Facebook again.")
                            return []
                else:
                    st.info("👆 Please open Facebook and log in first")
                    return []
            
            # Wait for marketplace page to load
            st.info("Waiting for Facebook marketplace page to load...")
            time.sleep(15)
            
            # Get initial count
            initial_count = self.get_listing_count()
            st.info(f"Initial Facebook listings found: {initial_count}")
            
            if initial_count == 0:
                st.warning("No Facebook listings found initially. Waiting and trying again...")
                time.sleep(15)
                initial_count = self.get_listing_count()
                st.info(f"Facebook second attempt: {initial_count} listings found")
                
                if initial_count == 0:
                    st.warning("Still no Facebook listings found. Continuing anyway - maybe listings will appear after scrolling...")
            
            # Perform infinite scroll to load all listings
            final_count = self.wait_and_scroll(scroll_attempts=max_scroll_attempts)
            
            # Extract detailed data from all listings
            all_listings = self.extract_all_listings()
            
            return all_listings
            
        except Exception as e:
            st.error(f"Error during Facebook scraping: {e}")
            import traceback
            st.text(traceback.format_exc())
            return []
        
        finally:
            # Clean up session state
            if 'fb_driver_ready' in st.session_state:
                del st.session_state.fb_driver_ready
            if 'fb_driver_instance' in st.session_state:
                del st.session_state.fb_driver_instance


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="Truck Listing Scraper",
        page_icon="🚛",
        layout="wide"
    )
    
    # App header
    st.title("🚛 Unified Truck Listing Scraper")
    st.markdown("Extract truck listings from **Craigslist** and **Facebook Marketplace** - Create Google Sheets automatically!")
    
    # Platform selection tabs
    tab1, tab2, tab3 = st.tabs(["🔧 Craigslist Scraper", "📱 Facebook Marketplace", "ℹ️ About"])
    
    # Check requirements once
    requirements_met = True
    
    # Check Google authentication (either secrets or file)
    google_auth_available = False
    if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
        st.sidebar.success("✅ Google Sheets (Streamlit secrets)")
        google_auth_available = True
    elif os.path.exists("service_account.json"):
        st.sidebar.success("✅ Google Sheets (local file)")
        google_auth_available = True
    else:
        st.sidebar.error("❌ Google Sheets authentication missing")
        requirements_met = False
    
    # ChromeDriver check (for local development)
    if os.path.exists("chromedriver"):
        st.sidebar.success("✅ ChromeDriver found")
    else:
        st.sidebar.warning("⚠️ ChromeDriver not found (may be provided by cloud environment)")
    
    if not google_auth_available:
        st.sidebar.error("Please set up Google Sheets authentication!")
    
    # Craigslist Tab
    with tab1:
        st.header("🔧 Craigslist Scraper")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Configure Craigslist Scraping")
            
            # Search URL input
            default_craigslist_url = "https://bend.craigslist.org/search/pickups-trucks?auto_bodytype=7&auto_bodytype=9&auto_transmission=2&max_auto_miles=70000&min_auto_year=2020&postal=97702&search_distance=40#search=2~list~0"
            craigslist_url = st.text_area(
                "Craigslist Search URL",
                value=default_craigslist_url,
                height=100,
                help="Paste your Craigslist search URL here"
            )
            
            # Max listings configuration
            max_listings_option = st.selectbox(
                "Number of listings to scrape",
                ["All listings", "10 (Test)", "25", "50", "100"],
                index=0,
                key="craigslist_max"
            )
            
            if max_listings_option == "All listings":
                max_listings = None
            else:
                max_listings = int(max_listings_option.split()[0])
            
            # Google Sheet name
            craigslist_sheet_name = st.text_input(
                "Google Sheet Name",
                value="Craigslist Truck Listings",
                help="Name for the Google Sheet that will be created",
                key="craigslist_sheet"
            )
            
            if st.button("🚀 Start Craigslist Scraping", type="primary", use_container_width=True, disabled=not google_auth_available):
                if not craigslist_url.strip():
                    st.error("Please provide a Craigslist search URL")
                elif not google_auth_available:
                    st.error("Please set up Google Sheets authentication first!")
                else:
                    # Start Craigslist scraping
                    with st.spinner("Initializing Craigslist scraper..."):
                        scraper = CraigslistScraper()
                    
                    st.info("🕐 This process may take several minutes depending on the number of listings...")
                    
                    # Run the scraping
                    listings = scraper.scrape_craigslist(craigslist_url, max_listings)
                    
                    if listings:
                        st.success(f"✅ Successfully scraped {len(listings)} Craigslist listings!")
                        
                        # Create Google Sheet directly from data
                        with st.spinner("Creating Google Sheet..."):
                            # Convert listings to DataFrame
                            df = pd.DataFrame(listings)
                            
                            sheets_manager = GoogleSheetsManager()
                            sheet_url, sheet_id = sheets_manager.create_sheet_from_dataframe(
                                df, 
                                craigslist_sheet_name
                            )
                            
                            if sheet_url:
                                st.balloons()
                                st.success("🎉 Craigslist Google Sheet created successfully!")
                                
                                # Display the link prominently
                                st.markdown("---")
                                st.markdown("### 🔗 Your Craigslist Google Sheet is ready!")
                                st.markdown(f"**[Click here to open your Google Sheet]({sheet_url})**")
                                st.code(sheet_url, language=None)
                                st.info("✅ The sheet is editable by anyone with the link")
                                
                                # Show summary
                                st.markdown("### 📊 Craigslist Summary")
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total Listings", len(listings))
                                with col2:
                                    st.metric("With Prices", len([l for l in listings if l['price']]))
                                with col3:
                                    st.metric("With Locations", len([l for l in listings if l['location']]))
                                with col4:
                                    st.metric("With VINs", len([l for l in listings if l['vin']]))
                                
                            else:
                                st.error("❌ Failed to create Google Sheet")
                    else:
                        st.error("❌ No Craigslist listings were successfully scraped")
        
        with col2:
            st.markdown("### 📊 Requirements Status")
            
            # Check requirements
            if os.path.exists("chromedriver"):
                st.success("✅ ChromeDriver found")
            else:
                st.warning("⚠️ ChromeDriver not in local directory")
                st.info("May be provided by cloud environment")
            
            if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
                st.success("✅ Google Sheets (Cloud secrets)")
            elif os.path.exists("service_account.json"):
                st.success("✅ Google Sheets (Local file)")
            else:
                st.error("❌ Google Sheets authentication missing")
    
    # Facebook Marketplace Tab
    with tab2:
        st.header("📱 Facebook Marketplace Scraper")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Configure Facebook Marketplace Scraping")
            
            # Search URL input
            default_facebook_url = "https://www.facebook.com/marketplace/108137335874390/search/?query=trucks&exact=false"
            facebook_url = st.text_area(
                "Facebook Marketplace URL",
                value=default_facebook_url,
                height=100,
                help="Paste your Facebook Marketplace search URL here"
            )
            
            # Max scroll attempts configuration
            max_scroll_attempts = st.slider(
                "Maximum scroll attempts",
                min_value=5,
                max_value=30,
                value=15,
                help="How many times to scroll down to load more listings"
            )
            
            # Google Sheet name
            facebook_sheet_name = st.text_input(
                "Google Sheet Name",
                value="Facebook Marketplace Truck Listings",
                help="Name for the Google Sheet that will be created",
                key="facebook_sheet"
            )
            
            # Check session status
            session_file = "facebook_session.pkl"
            if os.path.exists(session_file):
                st.success("✅ Saved Facebook session found - may be able to run in headless mode")
            else:
                st.info("ℹ️ No saved session - manual login will be required")
            
            if st.button("🚀 Start Facebook Scraping", type="primary", use_container_width=True, disabled=not google_auth_available):
                if not facebook_url.strip():
                    st.error("Please provide a Facebook Marketplace URL")
                elif not google_auth_available:
                    st.error("Please set up Google Sheets authentication first!")
                else:
                    # Start Facebook scraping
                    with st.spinner("Initializing Facebook scraper..."):
                        scraper = FacebookMarketplaceScraper()
                    
                    st.info("🕐 This process may take several minutes depending on the number of listings...")
                    
                    # Run the scraping
                    listings = scraper.scrape_facebook_marketplace(facebook_url, max_scroll_attempts)
                    
                    if listings:
                        st.success(f"✅ Successfully scraped {len(listings)} Facebook listings!")
                        
                        # Create Google Sheet directly from data
                        with st.spinner("Creating Google Sheet..."):
                            # Convert listings to DataFrame
                            df = pd.DataFrame(listings)
                            
                            sheets_manager = GoogleSheetsManager()
                            sheet_url, sheet_id = sheets_manager.create_sheet_from_dataframe(
                                df, 
                                facebook_sheet_name
                            )
                            
                            if sheet_url:
                                st.balloons()
                                st.success("🎉 Facebook Google Sheet created successfully!")
                                
                                # Display the link prominently
                                st.markdown("---")
                                st.markdown("### 🔗 Your Facebook Google Sheet is ready!")
                                st.markdown(f"**[Click here to open your Google Sheet]({sheet_url})**")
                                st.code(sheet_url, language=None)
                                st.info("✅ The sheet is editable by anyone with the link")
                                
                                # Show summary
                                st.markdown("### 📊 Facebook Summary")
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total Listings", len(listings))
                                with col2:
                                    st.metric("With Prices", len([l for l in listings if l['price'] != 'N/A']))
                                with col3:
                                    st.metric("With Locations", len([l for l in listings if l['location'] != 'N/A']))
                                with col4:
                                    st.metric("With Mileage", len([l for l in listings if l['mileage'] != 'N/A']))
                                
                            else:
                                st.error("❌ Failed to create Google Sheet")
                    else:
                        st.error("❌ No Facebook listings were successfully scraped")
                        
                    # Clean up driver if it exists
                    if hasattr(scraper, 'driver') and scraper.driver:
                        scraper.driver.quit()
        
        with col2:
            st.markdown("### 📊 Facebook Status")
            
            # Check Facebook session status
            session_file = "facebook_session.pkl"
            if os.path.exists(session_file):
                st.success("✅ Facebook session found")
                st.info("May run in headless mode")
            else:
                st.info("ℹ️ No saved Facebook session")
                st.warning("Manual login required")
            
            # Check requirements for Facebook
            if os.path.exists("chromedriver"):
                st.success("✅ ChromeDriver ready")
            else:
                st.warning("⚠️ ChromeDriver not in local directory")
                st.info("May be provided by cloud environment")
            
            if hasattr(st, 'secrets') and 'google_service_account' in st.secrets:
                st.success("✅ Google Sheets (Cloud secrets)")
            elif os.path.exists("service_account.json"):
                st.success("✅ Google Sheets (Local file)")
            else:
                st.error("❌ Google Sheets authentication missing")
    
    # About Tab
    with tab3:
        st.header("ℹ️ About This App")
        
        st.markdown("""
        ## 🎯 What This App Does
        
        This unified truck listing scraper combines the power of **Craigslist** and **Facebook Marketplace** 
        scraping into one convenient application. It extracts truck listings and automatically creates 
        Google Sheets that you can share with anyone.
        
        ## 🚀 Key Features
        
        ### **Craigslist Scraper**
        - ✅ **Comprehensive extraction** - Visits each listing individually
        - ✅ **15+ data points** - VIN, mileage, specs, location, maps
        - ✅ **Real-time progress** - Live updates during scraping
        - ✅ **Direct to Google Sheets** - No CSV files created
        
        ### **Facebook Marketplace Scraper**
        - ✅ **Session management** - Saves your login for future runs
        - ✅ **Infinite scroll** - Loads all available listings
        - ✅ **Smart login** - Headless mode when possible
        - ✅ **Duplicate removal** - Ensures unique listings only
        
        ## 📋 Requirements
        
        Before using this app, make sure you have:
        
        1. **ChromeDriver** - Download from [chromedriver.chromium.org](https://chromedriver.chromium.org/)
        2. **Google Service Account** - Set up at [Google Cloud Console](https://console.cloud.google.com/)
        3. **Valid search URLs** - From Craigslist or Facebook Marketplace
        
        ## 🔧 Setup Instructions
        
        ### **1. ChromeDriver Setup**
        ```bash
        # Download ChromeDriver and place in this directory
        # Make sure it matches your Chrome version
        chmod +x chromedriver  # On Mac/Linux
        ```
        
        ### **2. Google Sheets Setup**
        1. Go to [Google Cloud Console](https://console.cloud.google.com/)
        2. Create a new project or select existing
        3. Enable Google Sheets API and Google Drive API
        4. Create a Service Account
        5. Download JSON credentials
        6. Rename to `service_account.json` and place in this directory
        
        ### **3. Usage**
        1. Choose your platform tab (Craigslist or Facebook)
        2. Configure your search URL and settings
        3. Click "Start Scraping"
        4. Get your Google Sheet link!
        
        ## 🔒 Privacy & Security
        
        - **Local storage only** - All sessions stored on your machine
        - **No password storage** - Only cookies are saved
        - **Direct to Google Sheets** - No intermediate files created
        - **Full data ownership** - All extracted data belongs to you
        
        ## 💡 Tips for Best Results
        
        - **Start small** - Test with 10 listings first
        - **Stable internet** - Ensure good connection for best results
        - **Facebook sessions** - Login once, then it's automatic
        - **Custom searches** - Use specific filters for better results
        """)
        
        st.markdown("---")
        st.markdown("### 🛠️ Built With")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Frontend**\n- Streamlit\n- Python")
        with col2:
            st.markdown("**Scraping**\n- Selenium\n- ChromeDriver")
        with col3:
            st.markdown("**Data**\n- Google Sheets API\n- Pandas")


if __name__ == "__main__":
    main()
