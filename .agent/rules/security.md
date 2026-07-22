# Security Rules

- API key Gemini disimpan lewat config store (poin 4 di AGENTS.md), bukan
  hardcode di kode
- `.env` tidak pernah di-commit — cek `.gitignore` selalu mencakup `.env`
- Kalau `is_secret = true` di config store, jangan pernah tampilkan `value`
  asli di response API/log — mask jadi `••••••` di layer yang user-facing
- Endpoint `/chat` sebaiknya ada rate limiting sederhana kalau nanti dipakai
  publik (di luar scope belajar, tapi catat sebagai technical debt)
