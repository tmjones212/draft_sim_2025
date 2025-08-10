# Deploy Your Mock Draft Website RIGHT NOW

## Fastest Option: GitHub Pages (2 minutes)

### Step 1: Push to GitHub
```bash
# If you haven't set up a GitHub repo yet:
git remote add origin https://github.com/YOUR_USERNAME/mock_sim_2025.git
git push -u origin main
```

### Step 2: Enable GitHub Pages
1. Go to your repo on GitHub
2. Click **Settings** (top menu)
3. Scroll down to **Pages** (left sidebar)
4. Under "Source", select:
   - **Deploy from a branch**
   - Branch: **main**
   - Folder: **/ (root)**
5. Click **Save**

### Step 3: Access Your Site
- Wait 1-2 minutes
- Your site is live at: `https://YOUR_USERNAME.github.io/mock_sim_2025/`

That's it! You now have a real website!

---

## Alternative: Netlify (Even Easier - 30 seconds)

### No GitHub Required Method:
1. Go to [netlify.com](https://app.netlify.com/drop)
2. Drag the `index.html` file into the browser
3. Done! You get an instant URL like `https://amazing-draft-123.netlify.app`

### With GitHub (Auto-Updates):
1. Go to [netlify.com](https://netlify.com)
2. Sign up/Login with GitHub
3. Click "New site from Git"
4. Choose your repo
5. Deploy settings:
   - Build command: (leave empty)
   - Publish directory: `/`
6. Click "Deploy site"

---

## Option 3: Vercel (Also Super Easy)

1. Go to [vercel.com](https://vercel.com)
2. Sign up/Login with GitHub
3. Click "Import Project"
4. Import your GitHub repo
5. Click "Deploy"
6. Done! URL like: `https://mock-draft-2025.vercel.app`

---

## Option 4: Azure Static Web Apps

1. Go to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource"
3. Search "Static Web Apps"
4. Click "Create"
5. Fill in:
   - Resource Group: Create new
   - Name: `mock-draft-2025`
   - Plan: **Free**
   - Source: GitHub
   - Repository: Your repo
   - Branch: main
   - App location: `/`
6. Click "Create"
7. Your site: `https://mock-draft-2025.azurestaticapps.net`

---

## Which Should You Choose?

| Service | Setup Time | Custom Domain | Free Forever | Best For |
|---------|------------|---------------|--------------|----------|
| **GitHub Pages** | 2 min | ✅ | ✅ | Easiest if you have GitHub |
| **Netlify Drop** | 30 sec | ❌ | ✅ | Quickest test |
| **Netlify Git** | 3 min | ✅ | ✅ | Auto-updates |
| **Vercel** | 2 min | ✅ | ✅ | Fast global CDN |
| **Azure** | 5 min | ✅ | ✅ | Microsoft ecosystem |

## Pro Tips

### Custom Domain (Optional)
All services support custom domains like `mockdraft.com`:
1. Buy domain from Namecheap/GoDaddy ($10/year)
2. Add CNAME record pointing to your hosting
3. Configure in hosting settings

### Share With Friends
Once deployed, share the URL with anyone! They can:
- Access from any device
- Use it during your real draft
- No app install needed
- Works on phones, tablets, computers

### Updates
With GitHub integration, just:
```bash
git add .
git commit -m "Update"
git push
```
Site auto-updates in 1-2 minutes!

---

## Need the Python Version Instead?

If you want the full Python server with real player data:

### Option A: Replit (Free)
1. Go to [replit.com](https://replit.com)
2. Create new Python repl
3. Upload `web_app_simple.py` and folders
4. Click Run
5. Get URL like `https://mock-draft.YOUR_USERNAME.repl.co`

### Option B: Railway
1. Go to [railway.app](https://railway.app)
2. Deploy from GitHub
3. Add start command: `python web_app_simple.py`
4. Get URL instantly

### Option C: PythonAnywhere
1. Go to [pythonanywhere.com](https://pythonanywhere.com)
2. Free account
3. Upload files
4. Configure web app
5. URL: `YOUR_USERNAME.pythonanywhere.com`

---

## Quick Start Commands

```bash
# Test locally first
open index.html  # Mac
start index.html  # Windows
xdg-open index.html  # Linux

# Push to GitHub
git push

# Your site will be at one of these:
# https://YOUR_USERNAME.github.io/mock_sim_2025/
# https://YOUR_APP.netlify.app
# https://YOUR_APP.vercel.app
```