# 🚀 Deployment Guide

## Quick Deployment Checklist

### 1. GitHub Setup
```bash
cd truckScrapper
git init
git add .
git commit -m "Initial commit: Truck Listing Scraper"
git branch -M main
git remote add origin https://github.com/yourusername/truck-listing-scraper.git
git push -u origin main
```

### 2. Streamlit Cloud Deployment

1. **Go to [share.streamlit.io](https://share.streamlit.io)**
2. **Sign in with GitHub**
3. **Click "New app"**
4. **Select your repository: `truck-listing-scraper`**
5. **Set main file: `truck_listing_scraper.py`**
6. **Click "Advanced settings"**

### 3. Add Secrets in Streamlit Cloud

In the Advanced settings, paste your Google Service Account JSON as secrets:

```toml
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

### 4. Deploy!

Click "Deploy" and wait for your app to be live!

## 🔧 Local Development

### First Time Setup
```bash
pip install -r requirements.txt
```

### Download ChromeDriver (Local Only)
1. Check your Chrome version: `chrome://version/`
2. Download matching ChromeDriver from [chromedriver.chromium.org](https://chromedriver.chromium.org/)
3. Place in the `truckScrapper` directory
4. Make executable: `chmod +x chromedriver`
5. **Note**: ChromeDriver is excluded from Git and provided by Streamlit Cloud

### Add Google Credentials
1. Copy your `service_account.json` file to the `truckScrapper` directory
2. **DO NOT** commit this file to Git (it's in .gitignore)

### Facebook Session (Local Only)
- If you have an existing `facebook_session.pkl`, copy it to the directory
- This enables immediate headless Facebook scraping locally
- **Note**: Cloud deployment will require fresh Facebook login

### Run Locally
```bash
streamlit run truck_listing_scraper.py
```

## 📱 App Features

### Cloud Deployment (Streamlit Cloud)
- **✅ Craigslist Scraper**: 15+ detailed fields per listing
- **❌ Facebook Marketplace**: Not available (requires manual browser login)
- **✅ Google Sheets**: Automatic creation with public sharing
- **✅ ChromeDriver**: Provided by Streamlit Cloud
- **✅ Secure**: Uses cloud secrets for authentication

### Local Development
- **✅ Craigslist Scraper**: Full functionality
- **✅ Facebook Marketplace**: 5 focused fields with session management
- **✅ Google Sheets**: Automatic creation with public sharing
- **✅ ChromeDriver**: Local file or system PATH
- **✅ Secure**: Supports both local files and cloud secrets

## 🎯 Usage Tips

1. **Test locally first** with small limits (10 listings)
2. **Use specific search URLs** for better results
3. **For Facebook**: Login once, then sessions are saved
4. **Check requirements** in the sidebar before scraping

## 🆘 Troubleshooting

### Common Issues:

**"ChromeDriver not found"**
- Local: Download and place ChromeDriver in directory
- Cloud: This warning is normal, ChromeDriver is provided by Streamlit Cloud

**"Google Sheets authentication failed"**
- Local: Ensure `service_account.json` is present
- Cloud: Check secrets are properly configured

**"No listings found"**
- Verify your search URL is valid
- Try with a different search or broader criteria
- Check if the website structure has changed

### Environment Differences:

**Local Development:**
- ✅ Uses your ChromeDriver file (if present)
- ✅ Uses your Facebook session (immediate headless mode)
- ✅ Uses your local service_account.json

**Streamlit Cloud:**
- ✅ ChromeDriver provided by platform
- ❌ Facebook session invalid (requires fresh login)
- ✅ Uses secrets for Google authentication

### Getting Help:

1. Check this deployment guide
2. Review the main README.md
3. Check Streamlit Cloud logs for errors
4. Verify Google Cloud API permissions

### First Facebook Login on Cloud:

On Streamlit Cloud, Facebook scraping will require:
1. One-time manual login in visible browser mode
2. Session will be saved for future runs
3. Subsequent runs can use headless mode
