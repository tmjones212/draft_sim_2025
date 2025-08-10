# Mock Draft 2025 - Web Deployment Guide

## Three Ways to Access the Draft on Your Phone

### Option 1: Local Python Server (Full Features)
Run the Python server on your computer and access it from your phone on the same network:

```bash
# Run on your computer:
python3 web_app_simple.py
```

Then on your phone, open browser and go to:
- `http://YOUR_COMPUTER_IP:8080`
- The server will show you the exact URL when it starts

**Features**: Full draft functionality with real player data

### Option 2: Static HTML Version (Instant, No Setup)
Just open `index.html` in any browser on your phone:
1. Transfer `index.html` to your phone (email, cloud storage, etc.)
2. Open it in your phone's browser
3. Works offline, no server needed!

**Features**: Basic draft functionality with sample players

### Option 3: Azure Static Web Apps (Free Hosting)

#### Prerequisites
- Azure account (free tier available)
- GitHub repository

#### Deployment Steps

1. **Push code to GitHub:**
   ```bash
   git add index.html staticwebapp.config.json
   git commit -m "Add web version for mobile"
   git push
   ```

2. **Create Azure Static Web App:**
   - Go to [Azure Portal](https://portal.azure.com)
   - Click "Create a resource"
   - Search for "Static Web Apps"
   - Click "Create"
   - Fill in:
     - Resource Group: Create new or use existing
     - Name: `mock-draft-2025`
     - Plan type: **Free**
     - Region: Choose closest to you
     - Source: GitHub
     - Sign in to GitHub and authorize Azure
     - Organization: Your GitHub username
     - Repository: Your repo name
     - Branch: main
   - Build Details:
     - Build Presets: Custom
     - App location: `/`
     - API location: Leave empty
     - Output location: Leave empty
   - Click "Review + Create" then "Create"

3. **Access your app:**
   - After deployment (takes 2-3 minutes)
   - Your app will be available at:
   - `https://YOUR-APP-NAME.azurestaticapps.net`

#### Alternative Free Hosting Options

**GitHub Pages (Easiest):**
1. Go to your repo Settings → Pages
2. Source: Deploy from branch (main)
3. Folder: / (root)
4. Save
5. Access at: `https://YOUR-USERNAME.github.io/mock_sim_2025/`

**Netlify (Drag & Drop):**
1. Go to [netlify.com](https://netlify.com)
2. Drag the `index.html` file to the deployment area
3. Get instant URL

**Vercel:**
1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repo
3. Deploy with one click

## File Structure

```
web_app_simple.py     # Python server (local network access)
index.html           # Static HTML version (works anywhere)
staticwebapp.config.json  # Azure configuration
```

## Features Comparison

| Feature | Python Server | Static HTML | Azure/Cloud |
|---------|--------------|-------------|-------------|
| Real player data | ✅ | ❌ (sample) | ❌ (sample) |
| Custom ADP | ✅ | ❌ | ❌ |
| Works offline | ❌ | ✅ | ❌ |
| No setup | ❌ | ✅ | ❌ |
| Share with others | ❌ (local) | ❌ | ✅ |
| Free hosting | N/A | N/A | ✅ |

## Mobile Optimization

All versions are optimized for mobile with:
- Touch-friendly buttons
- Responsive layout
- Fast loading
- No dependencies
- Works on any modern mobile browser

## Running Locally for Development

```bash
# Python server (full features)
python3 web_app_simple.py

# Or just open index.html in browser (basic features)
```

## Notes
- The static HTML version uses sample player data
- For real player data, use the Python server
- All versions save draft state in browser (refreshing = reset)
- Azure Static Web Apps free tier includes:
  - 100 GB bandwidth/month
  - Custom domains
  - SSL certificates
  - Global CDN