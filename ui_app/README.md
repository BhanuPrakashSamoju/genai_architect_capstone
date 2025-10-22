# ui_app

Streamlit front-end for Loan Navigator.

Usage:

1. Copy `.env.example` to `.env` and update `API_BASE` if your backend is running on a different host/port.
2. Start the UI (from repo root or the ui_app folder):

```bash
# if using the repo root
streamlit run ui_app/app.py

# or from ui_app folder
cd ui_app
streamlit run app.py
```

Admin credentials are read from the top-level `.env` file (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_JWT_KEY`).

Security note: This demo stores tokens in Streamlit session state; secure your deployment and rotate admin keys and JWT secrets in production.
