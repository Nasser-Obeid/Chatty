# Chatty 💬

A modern, real-time messaging application built with Django. Chatty allows users to send instant messages, create group conversations, share files, and customize their experience with themes and backgrounds.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- **Real-time Messaging** - Messages appear instantly using WebSockets
- **User Authentication** - Secure signup, login, email verification, and magic link login
- **Message Encryption** - All messages encrypted with AES-256 before storage
- **Group Chats** - Create groups with multiple participants and admin roles
- **File Sharing** - Attach and download files in conversations
- **Chat Info Panel** - View user profiles, group members, and shared media
- **Themes** - Switch between dark and light modes
- **Chat Backgrounds** - Choose from multiple background styles
- **Message Caching** - Fast chat switching with sessionStorage caching
- **Chat Backup** - Export conversation history locally
- **Admin Panel** - Manage users, view activity logs, and monitor the platform

## 🛠️ Tech Stack

**Backend:**
- Django 4.2
- Django Channels (WebSockets)
- Daphne (ASGI Server)
- SQLite / PostgreSQL
- Redis (for production WebSocket layer)
- Cryptography (AES-256 encryption)

**Frontend:**
- HTML5 / CSS3 (with CSS custom properties for theming)
- Vanilla JavaScript
- Font Awesome icons
- Plus Jakarta Sans font

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/chatty.git
   cd chatty
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Open your browser**
   ```
   http://localhost:8000
   ```

## ⚙️ Environment Variables

Create a `.env` file in the project root for production:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key for security |
| `DEBUG` | Set to `False` in production |
| `ENCRYPTION_KEY` | 32-character key for message encryption |
| `DATABASE_URL` | PostgreSQL connection string (optional) |
| `REDIS_URL` | Redis server URL for WebSocket channels |

## 🚀 Deployment

### Docker

```bash
docker build -t chatty .
docker run -p 8000:8000 chatty
```

### Fly.io

```bash
fly launch
fly secrets set SECRET_KEY="your-secret-key" ENCRYPTION_KEY="your-encryption-key"
fly deploy
```

## 📁 Project Structure

```
chatty/
├── accounts/          # User authentication & profiles
├── chat/              # Messaging, WebSockets, conversations
├── core/              # Settings & general functionality
├── messenger/         # Project configuration
├── templates/         # HTML templates
├── static/            # CSS, JS, images
├── media/             # User uploads
├── manage.py
├── requirements.txt
├── Dockerfile
└── fly.toml
```

## 📸 Screenshots

![alt text](https://github.com/Nasser-Obeid/Chatty/blob/main/pics/Screenshot%202025-12-31%20at%2014-07-45%20Settings%20-%20Chatty.png?raw=true "screenshot1")
![alt text](/pics/Screenshot 2025-12-31 at 14-08-02 Sign In - Chatty.png?raw=true "screenshot2")
![alt text](/pics/Screenshot 2025-12-31 at 14-15-58 test - Chatty.png?raw=true "screenshot3")

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by WhatsApp and Telegram
- Built with Django and Django Channels
- Icons by Font Awesome

---

**Made with ❤️ using Django**
