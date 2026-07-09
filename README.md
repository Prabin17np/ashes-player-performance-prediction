# 🏏 Ashes Player Performance Prediction

A machine learning web application that predicts the batting performance of England and Australia players in future Ashes Test matches using historical Test cricket data.

This project was developed as a Final Year Undergraduate Thesis in Information Technology.

---

## 📌 Project Overview

The objective of this project is to predict an individual player's batting performance (runs scored) in future Ashes Test matches using historical player statistics and machine learning.

Unlike team-level prediction systems, this project focuses on **individual player performance**, making it useful for performance analysis, player comparison, and cricket analytics.

---

## ✨ Features

- Predict batting runs for an individual player
- Simulate multiple player performances for a future fixture
- Compare predicted player performances
- Interactive dashboard with charts
- View model evaluation metrics
- Player search from historical dataset
- REST API built with FastAPI
- Modern React frontend with responsive UI and animations

---

## 🧠 Machine Learning

### Prediction Target

- Individual player runs scored in an innings

### Training Dataset

- Test Matches
- England & Australia
- Years: **2010 – 2026**
- Source: Cricsheet

Dataset contains approximately:

- **6,652 batting innings**
- **165 unique players**

---

## 📊 Feature Engineering

The model uses **40 engineered features**, including:

### Career Statistics

- Career runs
- Career average
- Highest score
- Strike rate
- Number of fifties
- Number of centuries

### Recent Form

- Last 3 innings average
- Last 5 innings average
- Last 10 innings average
- Recent strike rate
- Consistency score

### Opponent Performance

- Runs vs current opponent
- Average vs opponent
- Strike rate vs opponent
- Dismissal rate
- Previous fifties and centuries

### Venue Features

- Runs at venue
- Average at venue
- Strike rate at venue
- Venue experience
- Venue scoring difficulty

### Team Context

- Team batting strength
- Team recent form
- Opponent bowling strength

### Match Context

- Venue
- Venue country
- Home / Away
- Innings number
- Batting position

---

## 🤖 Model Evaluation

Final selected model:

| Metric | Value |
|---------|------:|
| Algorithm | CatBoost Regressor |
| Training Samples | 6,652 |
| Features | 40 |
| CV MAE | 23.97 |
| CV RMSE | 33.95 |
| CV R² | 0.106 |
| Test MAE | 23.63 |
| Test RMSE | 34.29 |
| Test R² | 0.123 |

Several regression models were evaluated, including:

- CatBoost Regressor
- Random Forest
- HistGradientBoosting
- XGBoost
- Linear Regression
- Dummy Regressor

CatBoost achieved the best overall performance.

---

## 🏗 Project Structure

```
ashes-player-performance-prediction/
│
├── backend/          # FastAPI backend
├── frontend/         # React + TypeScript frontend
├── ml/               # ML pipeline and feature engineering
├── data/             # Historical dataset
├── output/           # Trained models
├── requirements.txt
└── README.md
```

---

## ⚙️ Backend

Built using:

- FastAPI
- Pydantic
- Pandas
- Joblib

Available endpoints:

| Endpoint | Description |
|-----------|-------------|
| `/health` | API health check |
| `/players` | List available players |
| `/predict` | Predict player runs |
| `/simulate` | Simulate multiple player predictions |
| `/model` | Model information and evaluation metrics |

---

## 💻 Frontend

Built using:

- React
- TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- Recharts
- Axios

Features include:

- Responsive interface
- Animated statistics cards
- Player comparison charts
- Prediction dashboard
- Simulation results
- Model information card

---

## 🚀 Installation

Clone the repository

```bash
git clone https://github.com/Prabin17np/ashes-player-performance-prediction.git
```

Move into the project

```bash
cd ashes-player-performance-prediction
```

Create virtual environment

```bash
python -m venv .venv
```

Activate

Linux/macOS

```bash
source .venv/bin/activate
```

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run backend

```bash
python -m uvicorn backend.app.main:app --reload
```

Run frontend

```bash
cd frontend

npm install

npm run dev
```

---

## 📈 Future Improvements

- Predict wickets for bowlers
- Predict batting average and strike rate
- Confidence intervals for predictions
- Feature importance visualization
- Match-level performance dashboard
- Deploy application to cloud

---

## 👨‍🎓 Author

**Prabin**

Final Year BSc (Hons) Computing Student

University Final Year Thesis Project

---

## 📄 License

This project is developed for educational and research purposes.
