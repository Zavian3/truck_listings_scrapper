# 🚛 Truck Listing Scraper

A unified Streamlit application for scraping truck listings from **Craigslist** and **Facebook Marketplace**, automatically creating Google Sheets with the extracted data.

## 🚀 Live Demo

Deploy this app on Streamlit Cloud: [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

## ✨ Features

- **🔧 Craigslist Scraper**: Comprehensive data extraction with 15+ fields
- **📱 Facebook Marketplace**: Smart session management with 5 focused fields *(Local development only)*
- **📊 Google Sheets Integration**: Direct data upload with public sharing
- **🎯 Unified Interface**: Both platforms in one clean app
- **⚡ Real-time Progress**: Live updates and progress tracking
- **☁️ Cloud-Ready**: Automatic platform detection for deployment

## 📋 Data Fields

### Craigslist (15+ fields)
- URL, Title, Price, Year, Make, Model
- VIN, Mileage, Cylinders, Drive, Fuel
- Color, Transmission, Type, Location
- Google Maps Link, Date Posted

### Facebook Marketplace (5 fields)
- URL, Title, Price, Mileage, Location

## 🛠️ Setup Instructions

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd truckScrapper
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Download ChromeDriver (Local Development Only)
1. Visit [ChromeDriver Downloads](https://chromedriver.chromium.org/)
2. Download the version matching your Chrome browser
3. Place the `chromedriver` executable in this directory
4. Make executable (Mac/Linux): `chmod +x chromedriver`

**Note**: ChromeDriver is automatically provided by Streamlit Cloud and excluded from Git.

### 4. Set Up Google Sheets API

#### Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable these APIs:
   - Google Sheets API
   - Google Drive API

#### Create Service Account
1. Go to IAM & Admin → Service Accounts
2. Click "Create Service Account"
3. Fill in name and description
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

#### Generate Credentials
1. Click on your service account
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Select "JSON" format
5. Download the file
6. Rename to `service_account.json`
7. Place in this directory

### 5. Run Locally
```bash
streamlit run truck_listing_scraper.py
```

## 🌐 Deploy on Streamlit Cloud

### 1. Push to GitHub
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub repository
4. Set main file: `truck_listing_scraper.py`
5. Add secrets in Advanced settings

### 3. Add Secrets
In Streamlit Cloud, go to Advanced settings and add:

```toml
# .streamlit/secrets.toml format
[google_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----"""
client_email = "your-service-account@your-project-id.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id.iam.gserviceaccount.com"
universe_domain = "googleapis.com"
```

## 🎯 Usage

### Local Development
1. **Choose Platform**: Select Craigslist or Facebook Marketplace tab
2. **Configure Settings**: 
   - Paste your search URL
   - Set number of listings (Craigslist)
   - Configure scroll attempts (Facebook)
   - Name your Google Sheet
3. **Start Scraping**: Click the start button
4. **Get Results**: Receive your Google Sheet link

### Cloud Deployment
- **✅ Craigslist**: Full functionality available
- **❌ Facebook**: Not available (manual login required)
- **Auto-detection**: App automatically detects environment

## ⚠️ Important Notes

### Rate Limiting & Ethics
- Built-in delays respect website terms
- Use responsibly and ethically
- Follow platform terms of service

### Facebook Login
- **Local**: Uses existing session if available, immediate headless mode
- **Cloud**: Requires fresh login on first run (sessions don't transfer)
- Session automatically saved for future runs in both environments
- May need periodic re-authentication

### Troubleshooting
- Ensure ChromeDriver matches your Chrome version
- Verify Google service account permissions
- Check search URLs are valid and accessible

## 📁 File Structure

```
truckScrapper/
├── truck_listing_scraper.py       # Main application
├── requirements.txt               # Python dependencies
├── service_account.json.example   # Sample credentials file
├── .streamlit/
│   └── config.toml                # Streamlit configuration
├── .gitignore                     # Git ignore rules
└── README.md                      # This file
```

## 🔒 Security

- **Never commit** `service_account.json` to version control
- Use Streamlit Cloud secrets for deployment
- Session files (`*.pkl`) are excluded from Git
- ChromeDriver is platform-specific and excluded

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📞 Support

For issues or questions:
1. Check existing GitHub issues
2. Review troubleshooting section
3. Create new issue with details

## 🎉 Success Tips

- **Test locally** before deploying
- **Use specific search terms** for better results
- **Start with small limits** (10 listings) for testing
- **Monitor Facebook sessions** for expiration
- **Verify Google Sheets permissions** when sharing

---

Built with ❤️ using Streamlit, Selenium, and Google Sheets API
