# Web App Setup Guide

This guide will help you set up the Telegram Web App for poll creation.

## Quick Start

1. **Host the Web App** (choose one):
   - **Vercel** (Recommended): Connect your GitHub repo, set root to `webapp/`
   - **Netlify**: Drag and drop the `webapp` folder
   - **Any static host**: Upload `webapp/index.html`

2. **Get your Web App URL** (must be HTTPS):
   - Example: `https://your-bot.vercel.app/index.html`
   - Or: `https://your-domain.com/webapp/index.html`

3. **Set environment variable**:
   ```bash
   # In your .env file
   WEBAPP_URL=https://your-bot.vercel.app/index.html
   ```

4. **Restart your bot** - The Web App button will now appear in inline queries!

## Development Setup

For local development and testing:

1. **Start the development server**:
   ```bash
   cd webapp
   python3 server.py
   ```

2. **Create HTTPS tunnel** (required for Telegram):
   ```bash
   # Install ngrok: https://ngrok.com/download
   ngrok http 8000
   ```

3. **Copy the HTTPS URL** from ngrok (e.g., `https://abc123.ngrok.io`)

4. **Set in .env**:
   ```bash
   WEBAPP_URL=https://abc123.ngrok.io/index.html
   ```

5. **Restart your bot**

## How It Works

1. User types `@yourbot` in a group chat
2. Inline query shows **"📝 Create Poll with Form"** option
3. User clicks button → Web App opens inside Telegram
4. User fills out the form with:
   - Poll question
   - Options (add/remove dynamically)
   - Anonymous/Public toggle
   - Forwarding toggle
   - Vote limit (optional)
5. Form submits data back to bot
6. Bot creates and sends the poll
7. Other users only see the final poll (not the creation process)

## Features

✅ **User-friendly form interface** - No more complex text parsing  
✅ **Works in groups** - No need to switch to private chat  
✅ **Clean UX** - Other users only see the poll, not the creation  
✅ **Theme support** - Automatically adapts to Telegram's light/dark mode  
✅ **Validation** - Client-side validation before submission  
✅ **Multi-language** - Uses bot's translation system  

## Troubleshooting

### Web App button doesn't appear
- Check that `WEBAPP_URL` is set in your `.env` file
- Ensure the URL is HTTPS (required by Telegram)
- Restart your bot after setting the environment variable

### Web App doesn't open
- Verify the URL is accessible (try opening in browser)
- Check that the URL uses HTTPS
- Ensure the HTML file is served correctly

### Form submission fails
- Check bot logs for error messages
- Verify the Web App URL is correct
- Ensure the bot has permission to send messages in the chat

### Development issues
- Make sure ngrok is running if testing locally
- Check that the port matches (default: 8000)
- Verify the ngrok URL is HTTPS (not HTTP)

## Production Deployment

### Vercel (Recommended)

1. Install Vercel CLI: `npm i -g vercel`
2. In your repo root:
   ```bash
   vercel --prod
   ```
3. Set root directory to `webapp` when prompted
4. Copy the deployment URL
5. Set `WEBAPP_URL=https://your-project.vercel.app/index.html`

### Netlify

1. Go to [Netlify](https://netlify.com)
2. Drag and drop the `webapp` folder
3. Copy the deployment URL
4. Set `WEBAPP_URL=https://your-site.netlify.app/index.html`

### Custom Server

Upload `webapp/index.html` to your web server and set:
```bash
WEBAPP_URL=https://your-domain.com/path/to/index.html
```

## Security Notes

- The Web App URL must use HTTPS (Telegram requirement)
- The form data is sent securely via Telegram's Web App API
- No sensitive data is stored in the Web App
- All validation happens server-side as well


