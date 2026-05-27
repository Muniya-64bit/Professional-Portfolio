# KVPL Frontend - Next.js

Professional tea plantation management system built with Next.js 14 and React 18.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:5000`

### Installation

```bash
# Install dependencies
npm install

# Create environment file (copy from .env.local template)
cp .env.local.example .env.local

# Start development server
npm run dev
```

Navigate to `http://localhost:3000`

### Build for Production

```bash
npm run build
npm start
```

## 📁 Project Structure

```
frontend/
├── app/
│   ├── layout.jsx          # Root layout with header/nav
│   ├── page.jsx            # Landing page (home)
│   ├── globals.css         # Global styles with CSS variables
│   ├── login/
│   │   └── page.jsx        # Login page with form
│   └── dashboard/
│       └── page.jsx        # Dashboard placeholder (coming soon)
├── .env.local              # Environment variables
├── next.config.js          # Next.js configuration
└── package.json
```

## 🎨 Design System

### Colors (CSS Variables)
- **Primary**: `--primary-dark` (#1b4332), `--primary-green` (#2d6a4f)
- **Accent**: `--accent-green` (#52b788)
- **Backgrounds**: `--light-bg` (#f1faee), `--card-white` (#ffffff)
- **Text**: `--text-dark` (#1a1a1a), `--text-muted` (#6b7280)

### Components
- Buttons: `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-outline`
- Cards: `.card` (white with shadow, hover effect)
- Forms: `.form-group`, input styling with focus states
- Layout: `.container`, `.grid`, `.flex`, `.flex-between`

### Responsive
- Mobile-first approach
- Breakpoint: 768px

## 📋 Pages

### Landing Page (`/`)
- Hero section with module overview
- Feature cards for ROI, Water, Fertilizer, Labour
- Stats section
- CTA buttons

### Login Page (`/login`)
- Email/password form
- Show/hide password toggle
- Demo account quick-fill
- Forgot password link
- Error handling

### Dashboard (`/dashboard`)
- Protected route (requires token)
- Welcome message
- Placeholder for 6 main modules
- Logout functionality

## 🔐 Authentication

Currently configured for demo login:
- **Email**: admin@kundasale.com
- **Password**: demo123

Token stored in `localStorage['token']`. Update authentication logic in:
- `app/login/page.jsx` - Login form submission
- `app/dashboard/page.jsx` - Token verification

## 🔗 API Integration

Backend API endpoints expected:
- `POST /api/auth/login` - User authentication
- `GET /api/user` - Get current user
- `GET /api/estates` - List estates
- `GET /api/dashboard/roi` - ROI data
- And more for each module...

## 📱 Mobile Support

Fully responsive design using CSS Grid and Flexbox:
- Mobile: Single column layout
- Tablet: 2-column grid where applicable
- Desktop: 3+ column grid

## 🛠️ Development

### Running Tests
```bash
npm run lint
```

### File Structure for New Pages
```jsx
'use client';

import { useState, useEffect } from 'react';

export default function NewPage() {
  return (
    <main>
      {/* Your content */}
    </main>
  );
}
```

## 🚀 Next Steps

1. **Build Dashboard Modules** (Priority Order):
   - ROI Calculator with trend charts
   - Water Efficiency status cards
   - Fertilizer rotation planner
   - Labour allocation optimizer

2. **API Integration**:
   - Connect login to backend `/api/auth/login`
   - Fetch real data from database
   - Implement proper error handling

3. **Add Chart Library**:
   - Recommend: `recharts` or `chart.js`
   - For ROI trends and water usage visualization

4. **State Management**:
   - Consider `zustand` or `context-api` for global state
   - For user auth, selected estate, filter states

## 📦 Dependencies

- **next**: 14.2.5
- **react**: 18.3.1
- **react-dom**: 18.3.1

### Recommended Additions
- `axios` - HTTP requests
- `recharts` - Charts
- `zustand` - State management
- `tailwindcss` - Alternative to custom CSS (optional)

## 📞 Support

For issues or questions about the frontend setup, check:
1. Backend API is running (`http://localhost:5000`)
2. Environment variables in `.env.local`
3. Network tab in browser DevTools for API errors
4. Console for JavaScript errors

---

**Built for KVPL System** 🌿
