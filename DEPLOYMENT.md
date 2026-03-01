# GitHub Pages Deployment

## Quick Setup

1. Create a new repository on GitHub
2. Push this code to the repository:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

3. Enable GitHub Pages:
   - Go to repository `Settings` → `Pages`
   - Under **Source**: select `Deploy from a branch`
   - Under **Branch**: select `main` and `/docs`, then click `Save`
   - Wait 1-3 minutes
   - Site will be available at: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

## Automated Data Updates

The included GitHub Action updates data automatically every 2 hours.

### Enable Actions Permissions
1. `Settings` → `Actions` → `General`
2. Under **Workflow permissions**: select `Read and write permissions`
3. Click `Save`

### Manual Trigger
Go to `Actions` → "Update Alert Data" → "Run workflow"

## Troubleshooting

**Site not loading:**
- Verify branch is `main` and folder is `/docs`
- Check that `docs/.nojekyll` file exists
- Wait 2-3 minutes after changes

**Data not updating:**
- Verify Actions is enabled in settings
- Check Actions tab for errors
- Confirm Write permissions are enabled

**JavaScript not working:**
- Open Developer Tools (F12)
- Check Console for errors
- Verify CSS/JS paths are correct
