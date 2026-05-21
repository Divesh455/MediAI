# MediAI - Healthcare AI Platform Frontend

A fully functional healthcare AI platform frontend built with **HTML, CSS, JavaScript, and Bootstrap 5**.

## Project Structure

### Pages (11 routes)
- **/** - Landing page with features and benefits
- **/login** - User authentication
- **/register** - User registration
- **/dashboard** - Main dashboard with health stats and charts
- **/predict** - AI disease prediction with symptom analysis
- **/chatbot** - Health chatbot interface
- **/xray** - Medical image upload and analysis
- **/reports** - Health report management
- **/history** - Activity timeline
- **/profile** - User profile and health info
- **/settings** - Theme, notifications, privacy, security settings

### File Organization

```
project/
├── app/                      # Next.js page routes
│   ├── page.tsx             # Home
│   ├── login/page.tsx       # Login
│   ├── register/page.tsx    # Register
│   ├── dashboard/page.tsx   # Dashboard
│   ├── predict/page.tsx     # Prediction
│   ├── chatbot/page.tsx     # Chatbot
│   ├── xray/page.tsx        # X-Ray analysis
│   ├── reports/page.tsx     # Reports
│   ├── history/page.tsx     # History
│   ├── profile/page.tsx     # Profile
│   └── settings/page.tsx    # Settings
│
├── public/                   # Static assets
│   ├── *.html               # HTML page files
│   ├── css/
│   │   └── style.css        # Design system and styling
│   ├── js/
│   │   └── app.js           # JavaScript utilities
│   └── *.{jpg,png,svg}      # Images and icons
│
└── [config files]           # Next.js config, TypeScript, etc.
```

## Features

### Design System
- **Glassmorphism effects** with backdrop blur
- **Blue-cyan gradient** primary color (#00d4ff)
- **CSS variables** for easy theming
- **Dark/light mode** toggle with localStorage persistence
- **Smooth animations** and hover effects
- **Responsive Bootstrap 5 grid** system

### Interactive Components
- Mobile-responsive sidebar navigation
- Dark/light theme switcher
- Form validation helpers
- Notification system
- Typing animations
- Drag-and-drop image upload
- Activity timeline with visual indicators
- Interactive health charts (Chart.js ready)
- Real-time chatbot message interface

### JavaScript Modules
- **app.js** - Core app logic including:
  - Theme toggle functionality
  - Navigation management
  - Notification system
  - MediAIApi wrapper class for backend integration
  - Local storage management
  - AOS scroll animations

## Technology Stack

- **HTML5** - Semantic markup
- **CSS3** - Custom styling with CSS variables
- **Bootstrap 5** - Responsive grid and components
- **JavaScript (ES6+)** - Client-side interactivity
- **Font Awesome** - Icon library
- **AOS (Animate On Scroll)** - Scroll animations
- **Chart.js** - Data visualization (placeholder support)

## Getting Started

### Run Dev Server
```bash
pnpm dev
```

The app will be available at `http://localhost:3000`

### Build for Production
```bash
pnpm build
pnpm start
```

## API Integration

The frontend is ready to connect to a FastAPI backend. JavaScript makes requests to these endpoints:

```javascript
// Available in MediAIApi class (js/app.js)
await api.predict(symptoms)        // POST /predict
await api.chat(message)            // POST /chat
await api.analyzeXray(image)       // POST /analyze-xray
await api.getReports()             // GET /reports
await api.analyzeReport(reportId)  // POST /analyze-report
```

## Styling & Customization

All colors and design tokens are defined in `public/css/style.css`:

```css
:root {
  --primary: #00d4ff;          /* Cyan accent */
  --primary-dark: #0099cc;     /* Dark cyan */
  --bg-dark: #0f1419;          /* Dark background */
  --bg-darker: #0a0e13;        /* Darker background */
  --text-light: #e0e6ed;       /* Light text */
  --border-color: #1e2838;     /* Border color */
}
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Next Steps

1. **Backend Integration** - Connect API endpoints from `public/js/app.js`
2. **Database Setup** - Store user profiles, health data, analysis results
3. **Authentication** - Implement secure login/registration
4. **Real-time Updates** - Add WebSocket support for live data
5. **Push Notifications** - Browser notifications for health alerts

---

**Status**: ✅ Frontend complete and fully functional
**Last Updated**: May 21, 2026
