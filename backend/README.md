# Gym Membership Mock Backend

FastAPI mock server cho chatbot tư vấn gói tập gym, dùng SQLite + SQLAlchemy.

## 1) Cài đặt và chạy app

Yêu cầu: Python 3.9+

```bash
cd /Users/minhkha/SidePrj/gym-agent/backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Chạy server:

```bash
uvicorn backend.main:app --reload --port 8000
```

Mở docs:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

> Luu y: app se tu dong tao `gym.db` va seed data khi khoi dong lan dau.

---

## 2) Quick health check

```bash
curl -s http://127.0.0.1:8000/health
```

---

## 3) Test full API bang curl

Dat base URL:

```bash
BASE_URL="http://127.0.0.1:8000"
```

### A. Packages APIs

1. Lay tat ca goi:

```bash
curl -s "$BASE_URL/packages/search"
```

2. Search theo tu khoa:

```bash
curl -s "$BASE_URL/packages/search?q=monthly"
```

3. Filter theo tier:

```bash
curl -s "$BASE_URL/packages/search?tier=PLUS"
```

4. Filter theo gia toi da:

```bash
curl -s "$BASE_URL/packages/search?max_price=900000"
```

5. Ket hop filter:

```bash
curl -s "$BASE_URL/packages/search?q=yearly&tier=STANDARD&max_price=600000"
```

6. Lay chi tiet 1 goi (theo code):

```bash
curl -s "$BASE_URL/packages/PKG_E_M01"
```

7. Compare nhieu goi:

```bash
curl -s "$BASE_URL/packages/compare?ids=PKG_E_M01,PKG_S_M01,PKG_P_M01"
```

8. Case loi compare (<2 id):

```bash
curl -i "$BASE_URL/packages/compare?ids=PKG_E_M01"
```

9. Case loi package khong ton tai:

```bash
curl -i "$BASE_URL/packages/UNKNOWN_CODE"
```

### B. Facilities API

1. Lay toan bo facilities:

```bash
curl -s "$BASE_URL/facilities"
```

2. Filter theo category:

```bash
curl -s "$BASE_URL/facilities?category=cardio"
curl -s "$BASE_URL/facilities?category=strength"
curl -s "$BASE_URL/facilities?category=free_weights"
curl -s "$BASE_URL/facilities?category=functional"
curl -s "$BASE_URL/facilities?category=recovery"
```

### C. Slots + Bookings APIs

1. Lay slots available theo ngay (hom nay):

```bash
TODAY=$(date +%F)
curl -s "$BASE_URL/slots?date=$TODAY"
```

2. Tao booking (chon 1 gio future, vi du 19:00):

```bash
APPOINTMENT_DT="$(date +%F)T19:00:00"
curl -s -X POST "$BASE_URL/bookings" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_name\": \"Nguyen Van A\",
    \"phone\": \"0901234567\",
    \"appointment_dt\": \"$APPOINTMENT_DT\",
    \"note\": \"Tu van goi Plus\"
  }"
```

3. Kiem tra slot vua dat da bi khoa (khong con available):

```bash
curl -s "$BASE_URL/slots?date=$(date +%F)"
```

4. Lay chi tiet booking theo ref:

```bash
BOOKING_REF="<PASTE_BOOKING_REF_HERE>"
curl -s "$BASE_URL/bookings/$BOOKING_REF"
```

5. Case loi booking voi thoi gian qua khu:

```bash
curl -i -X POST "$BASE_URL/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Past",
    "phone": "0900000000",
    "appointment_dt": "2020-01-01T10:00:00",
    "note": "should fail"
  }'
```

6. Case loi booking trung slot da dat:

```bash
curl -i -X POST "$BASE_URL/bookings" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_name\": \"Test Duplicate\",
    \"phone\": \"0911111111\",
    \"appointment_dt\": \"$APPOINTMENT_DT\",
    \"note\": \"duplicate slot\"
  }"
```

7. Case loi booking_ref khong ton tai:

```bash
curl -i "$BASE_URL/bookings/BK-20990101-9999"
```

---

## 4) Goi y test dep hon voi jq (optional)

Neu may da cai `jq`:

```bash
curl -s "$BASE_URL/packages/search?tier=PLUS" | jq
curl -s "$BASE_URL/facilities?category=cardio" | jq
```

---

## 5) Cau truc backend

```text
backend/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── seed.py
├── routers/
│   ├── packages.py
│   ├── facilities.py
│   └── bookings.py
└── requirements.txt
```
