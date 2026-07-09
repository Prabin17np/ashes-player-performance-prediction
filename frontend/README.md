# Ashes Cricket Player Performance Prediction — Frontend

React + TypeScript + Vite dashboard for the Ashes Cricket Player Performance
Prediction System. Talks to the existing FastAPI backend (`GET /health`,
`GET /players`, `POST /predict`, `POST /simulate`) — no backend code is
included or modified.

## Setup

```bash
npm install
```

## Run in development

The dev server proxies `/api/*` to `http://127.0.0.1:8000` (see
`vite.config.ts`), so start your FastAPI backend first, then:

```bash
npm run dev
```

Open http://localhost:3000.

## Point at a different backend

Copy `.env.example` to `.env` and set `VITE_API_BASE_URL` to your backend's
root URL (used directly, bypassing the dev proxy):

```bash
cp .env.example .env
# VITE_API_BASE_URL=https://your-backend.example.com
```

## Build for production

```bash
npm run build
npm run preview
```

## Project structure

```
src/
  components/   Reusable UI (buttons, cards, charts, forms, layout, etc.)
  pages/        One file per route (Home, Predict, Simulate, Players, About)
  layouts/      MainLayout (navbar + footer + page transitions)
  services/     Axios API client + one module per backend endpoint group
  hooks/        useHealth, usePlayers, usePrediction, useSimulation
  types/        TypeScript types mirroring the backend's Pydantic schemas
```

## Design

Navy (`#16335C`), white, light gray, and an Ashes-urn gold accent
(`#C79A3C`). Headings use Fraunces, UI text uses Inter, and every stat/score
uses JetBrains Mono with tabular figures in a scoreboard-style treatment —
the app's one recurring signature motif.
