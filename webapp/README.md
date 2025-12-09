# Telegram Web App for Poll Creation

This directory contains the Web App (Mini App) for creating polls via a user-friendly form interface.

## Quick Setup

1. **Host the Web App** (choose one):
   - **Vercel**: Deploy by connecting your GitHub repo, set root to `webapp/`
   - **Netlify**: Drag and drop the `webapp` folder
   - **GitHub Pages**: Enable Pages in repo settings
   - **Cloudflare Pages**: Connect your repo
   - **Any web server**: Upload `index.html` to your server

2. **Get your Web App URL** (must be HTTPS):
   - Example: `https://your-bot.vercel.app/index.html`

3. **Set environment variable**:
   ```bash
   # In your .env file
   WEBAPP_URL=https://your-bot.vercel.app/index.html
   ```

4. **Restart your bot** - The Web App button will now appear in inline queries!

## Development Setup

For local testing:

```bash
cd webapp
python3 server.py
```

Then use a tunneling service like ngrok to get HTTPS:
```bash
ngrok http 8000
```

Use the HTTPS URL from ngrok as your Web App URL (e.g., `https://abc123.ngrok.io/index.html`)

## How It Works

1. User types `@yourbot` in a group chat
2. Inline query shows **"📝 Create Poll with Form"** option
3. User clicks button → Web App opens inside Telegram
4. User fills out the form:
   - Poll question
   - Options (add/remove dynamically)
   - Anonymous/Public toggle
   - Forwarding toggle
   - Vote limit (optional)
5. Form submits data back to bot via `tg.sendData()`
6. Bot receives data and creates the poll
7. Poll appears in the chat - other users only see the final poll!

## Features

✅ **User-friendly form interface** - No more complex text parsing  
✅ **Works in groups** - No need to switch to private chat  
✅ **Clean UX** - Other users only see the poll, not the creation  
✅ **Theme support** - Automatically adapts to Telegram's light/dark mode  
✅ **Validation** - Client-side and server-side validation  
✅ **Multi-language** - Uses bot's translation system  

## File Structure

```
webapp/
├── index.html          # Main Web App form
├── server.py           # Development server script
└── README.md          # This file
```

## Customization

You can customize the form by editing `index.html`:
- Change colors to match your bot's theme
- Add more fields
- Modify validation rules
- Adjust styling

The Web App automatically adapts to Telegram's theme (light/dark mode).

## Troubleshooting

- **Web App button doesn't appear**: Check that `WEBAPP_URL` is set and bot is restarted
- **Web App doesn't open**: Verify URL is HTTPS and accessible
- **Form submission fails**: Check bot logs for error messages

See `SETUP_WEBAPP.md` in the root directory for detailed setup instructions.
