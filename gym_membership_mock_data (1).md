# Gym Membership Mock Data Design

## 1. Tier System & Amenities Overview

### 1.1. Membership Tiers

- **Essential**
  - Entry-level, giá thấp, tập máy & tạ cơ bản.
  - Không có pool/sauna, không towel service.
  - Có private locker.

- **Standard**
  - Phù hợp người tập đều, thêm group class cơ bản (yoga, HIIT).
  - Có **sauna** dùng chung.
  - Không có pool, không towel service (tự mang khăn).
  - Private locker.

- **Plus**
  - Nâng cấp rõ so với Standard, target dân văn phòng.
  - Có **pool + sauna**.
  - Có **towel service** (khăn tắm/khăn tập).
  - Guest pass giới hạn mỗi tháng.
  - Private locker (fixed hoặc ưu tiên).

- **Premium**
  - Full access: **pool + sauna + towel service**.
  - Priority booking lớp, giảm giá spa/massage, 1 buổi PT định kỳ.
  - Private locker khu vực riêng (có sấy tóc, amenities tốt hơn).

- **Elite (VIP)**
  - Full access tất cả tiện ích: pool, sauna, towel service.
  - Nhiều buổi PT/tháng, guest pass nhiều, ưu tiên booking giờ cao điểm.
  - Private locker premium (có ổ cắm, charging).

### 1.2. Amenities Model

**Base amenities (mặc định mọi tier):**
- **Gym Floor Access**: cardio, weight machines, free weights.
- **Private Locker**: tủ đồ cá nhân.

**Optional amenities:**
- **Pool Access**: hồ bơi.
- **Sauna Access**: sauna/steam room.
- **Towel Service**: khăn tập/khăn tắm.

**Service-level perks:**
- Group classes (yoga, HIIT, dance, cycling).
- Personal training sessions (included / discounted).
- Guest passes.
- Discount on spa/massage.
- Priority booking for classes.

---

## 2. Bảng Chi Tiết Các Gói Tập

| Package ID  | Package Name         | Tier      | Billing Plan         | Price/tháng (VND) | Commit Term  | Pool | Sauna | Towel | Locker  | Group Class    | PT /tháng | Guest Pass /tháng | Notes                         |
|-------------|----------------------|-----------|----------------------|-------------------|--------------|------|-------|-------|---------|----------------|-----------|-------------------|-------------------------------|
| PKG_E_M01   | Essential Monthly    | Essential | Monthly              | 399.000           | Không        | ❌   | ❌    | ❌    | ✅      | ❌             | 0         | 0                 | Entry-level, linh hoạt        |
| PKG_E_Q03   | Essential Quarterly  | Essential | Trả trước 3 tháng    | 349.000           | 3 tháng      | ❌   | ❌    | ❌    | ✅      | ❌             | 0         | 0                 | Giảm nhẹ so với monthly       |
| PKG_E_Y12   | Essential Yearly     | Essential | Trả trước 12 tháng   | 299.000           | 12 tháng     | ❌   | ❌    | ❌    | ✅      | ❌             | 0         | 2/năm             | Tặng guest pass               |
| PKG_S_M01   | Standard Monthly     | Standard  | Monthly              | 599.000           | Không        | ❌   | ✅    | ❌    | ✅      | ✅ (basic)     | 0         | 1                 | Thêm sauna + lớp cơ bản       |
| PKG_S_Q03   | Standard Quarterly   | Standard  | Trả trước 3 tháng    | 549.000           | 3 tháng      | ❌   | ✅    | ❌    | ✅      | ✅ (basic)     | 0         | 2                 |                               |
| PKG_S_Y12   | Standard Yearly      | Standard  | Trả trước 12 tháng   | 499.000           | 12 tháng     | ❌   | ✅    | ❌    | ✅      | ✅ (basic)     | 1 onboard | 3                 | Value tốt, phổ biến nhất      |
| PKG_P_M01   | Plus Monthly         | Plus      | Monthly              | 899.000           | Không        | ✅   | ✅    | ✅    | ✅      | ✅ (full)      | 1         | 2                 | Pool + sauna + towel          |
| PKG_P_Q03   | Plus Quarterly       | Plus      | Trả trước 3 tháng    | 849.000           | 3 tháng      | ✅   | ✅    | ✅    | ✅      | ✅ (full)      | 1         | 3                 | Target dân văn phòng          |
| PKG_P_Y12   | Plus Yearly          | Plus      | Trả trước 12 tháng   | 799.000           | 12 tháng     | ✅   | ✅    | ✅    | ✅      | ✅ (full)      | 2         | 4                 | Giá tốt nhất tier này         |
| PKG_PR_M01  | Premium Monthly      | Premium   | Monthly              | 1.399.000         | Không        | ✅   | ✅    | ✅    | ✅ VIP  | ✅ (priority)  | 2         | 4                 | Khu locker riêng, ưu tiên lớp |
| PKG_PR_Q03  | Premium Quarterly    | Premium   | Trả trước 3 tháng    | 1.299.000         | 3 tháng      | ✅   | ✅    | ✅    | ✅ VIP  | ✅ (priority)  | 2         | 5                 | Spa discount 10%              |
| PKG_PR_Y12  | Premium Yearly       | Premium   | Trả trước 12 tháng   | 1.199.000         | 12 tháng     | ✅   | ✅    | ✅    | ✅ VIP  | ✅ (priority)  | 3         | 6                 | Target khách hàng trung thành |
| PKG_V_M01   | Elite Monthly        | Elite     | Monthly              | 2.199.000         | Không        | ✅   | ✅    | ✅    | ✅ VIP+ | ✅ (priority)  | 4         | 8                 | Full perks, giờ cao điểm      |
| PKG_V_Y12   | Elite Yearly         | Elite     | Trả trước 12 tháng   | 1.899.000         | 12 tháng     | ✅   | ✅    | ✅    | ✅ VIP+ | ✅ (priority)  | 6         | 10                | Spa discount 20%              |

---

## 3. Facilities — Danh Sách Thiết Bị Phòng Gym

### 3.1. Mock Data Schema

Mỗi thiết bị lưu theo schema sau để phục vụ semantic search (ChromaDB collection: `gym_facilities`):

```json
{
  "id": "FAC_CARDIO_TREADMILL_01",
  "name": "Treadmill",
  "category": "cardio",
  "muscle_groups": ["legs", "glutes", "cardio"],
  "description": "Máy chạy bộ điện có thể điều chỉnh tốc độ và độ dốc, phù hợp đi bộ và chạy.",
  "aliases": ["máy chạy bộ", "treadmill"],
  "brand": "Life Fitness",
  "quantity": 8,
  "available": true
}
```

> **Lý do có `aliases` và `muscle_groups`:** user có thể hỏi "máy tập ngực", "máy leo cầu thang", "máy skiing" — semantic search trên các field này sẽ match tốt hơn keyword search trên tên máy.

---

### 3.2. Cardio Machines

| ID                      | Tên                      | Nhóm cơ / Mục tiêu                          | Số lượng | Notes                                   |
|-------------------------|--------------------------|----------------------------------------------|----------|-----------------------------------------|
| FAC_CARDIO_TREADMILL    | Treadmill                | Legs, glutes, cardio endurance               | 8        | Máy chạy bộ điện, chỉnh tốc độ & dốc   |
| FAC_CARDIO_ELLIPTICAL   | Elliptical / Cross Trainer| Full body, low-impact cardio                | 4        | Giảm áp lực khớp, phù hợp phục hồi     |
| FAC_CARDIO_BIKE_UPRIGHT | Upright Bike             | Quads, hamstrings, cardio                    | 4        | Xe đạp đứng, nhẹ nhàng cho người mới   |
| FAC_CARDIO_BIKE_SPIN    | Spin Bike                | Quads, glutes, calves, cardio                | 10       | Dùng cho lớp Indoor Cycling             |
| FAC_CARDIO_ROWER        | Rowing Machine (Row Erg) | Back, arms, legs, core — full body cardio    | 4        | Máy chèo thuyền, tốt cho lưng & sức bền|
| FAC_CARDIO_STAIRCLIMBER | Stair Climber / Stepmill | Glutes, quads, hamstrings, calves            | 3        | Máy leo cầu thang xoay, đốt mỡ cao     |
| FAC_CARDIO_SKIERG       | Ski Ergometer (SkiErg)   | Shoulders, triceps, core, cardio             | 2        | Mô phỏng trượt tuyết, phổ biến CrossFit|
| FAC_CARDIO_RECUMBENT    | Recumbent Bike           | Quads, hamstrings, low-impact cardio         | 2        | Xe đạp ngả lưng, phù hợp người cao tuổi|

---

### 3.3. Strength Machines

| ID                      | Tên                        | Nhóm cơ chính                        | Số lượng | Notes                                        |
|-------------------------|----------------------------|--------------------------------------|----------|----------------------------------------------|
| FAC_STR_CHESTPRESS      | Chest Press Machine        | Chest, triceps, anterior deltoid     | 2        | Máy tập ngực chuyên biệt dạng pin-loaded     |
| FAC_STR_PECFLY          | Pec Deck / Chest Fly       | Chest (inner), anterior deltoid      | 2        | Máy căng ngực, cô lập cơ ngực hiệu quả       |
| FAC_STR_LATPULLDOWN     | Lat Pulldown Machine       | Lats, biceps, rear deltoid           | 2        | Máy kéo xô, tập lưng rộng                    |
| FAC_STR_SEATEDROW       | Seated Row Machine         | Mid-back, lats, biceps               | 2        | Máy kéo lưng giữa ngồi                       |
| FAC_STR_CABLE           | Cable Machine / Functional Trainer | Full body (versatile)        | 4        | Máy cáp đa năng, nhiều bài tập               |
| FAC_STR_SMITHMACHINE    | Smith Machine              | Quads, chest, shoulders (versatile)  | 2        | Thanh bar cố định, squat/bench/press         |
| FAC_STR_LEGPRESS        | Leg Press Machine          | Quads, glutes, hamstrings            | 2        | Máy đẩy chân nằm/ngồi góc 45°               |
| FAC_STR_LEGEXTENSION    | Leg Extension Machine      | Quadriceps                           | 2        | Máy duỗi chân, cô lập đùi trước              |
| FAC_STR_LEGCURL         | Leg Curl Machine           | Hamstrings                           | 2        | Máy gập chân, cô lập đùi sau                 |
| FAC_STR_SHOULDERPRESS   | Shoulder Press Machine     | Deltoids, triceps                    | 2        | Máy đẩy vai ngồi                             |
| FAC_STR_CALFPRESS       | Calf Raise Machine         | Calves (gastrocnemius, soleus)       | 1        | Máy kiễng gót tập bắp chân                   |
| FAC_STR_HIPABDUCT       | Hip Abduction/Adduction    | Glutes, inner & outer thigh          | 1        | Máy dạng/khép đùi                            |
| FAC_STR_BACKEXTENSION   | Back Extension Machine     | Lower back, glutes, hamstrings       | 1        | Máy ưỡn lưng dưới                            |
| FAC_STR_ASSISTEDPULLUP  | Assisted Pull-up/Dip Machine | Lats, biceps, triceps, chest       | 1        | Máy hỗ trợ pullup/dip cho người mới          |

---

### 3.4. Free Weights & Functional Area

| ID                      | Tên                        | Nhóm cơ / Mục tiêu                       | Số lượng | Notes                                     |
|-------------------------|----------------------------|-------------------------------------------|----------|-------------------------------------------|
| FAC_FREE_DUMBBELL       | Dumbbell Rack (1–40kg)     | Full body                                 | 1 bộ     | Đủ tạ đôi từ 1kg đến 40kg                 |
| FAC_FREE_BARBELL        | Olympic Barbell + Plates   | Full body (squat, deadlift, bench)        | 6 bộ     | Thanh Olympic 20kg, đĩa bumper + standard |
| FAC_FREE_BENCH_FLAT     | Flat Bench                 | Chest, shoulders, triceps                 | 4        | Ghế nằm ngang                             |
| FAC_FREE_BENCH_INCLINE  | Incline/Decline Bench      | Upper/lower chest, shoulders              | 4        | Ghế điều chỉnh góc                        |
| FAC_FREE_SQUAT_RACK     | Power Rack / Squat Rack    | Full body compound                        | 3        | Khung tập squat/deadlift/press            |
| FAC_FUNC_KETTLEBELL     | Kettlebell Set (4–32kg)    | Full body, functional strength            | 1 bộ     | Từ 4kg đến 32kg                           |
| FAC_FUNC_TRX            | TRX Suspension Trainer     | Core, full body                           | 4        | Dây treo tập cân bằng và core             |
| FAC_FUNC_BATTLEROPE     | Battle Ropes               | Arms, shoulders, core, cardio             | 2 cặp    | Dây chiến, cardio kết hợp sức mạnh        |
| FAC_FUNC_MEDBALL        | Medicine / Slam Balls      | Core, explosive power                     | 1 bộ     | 3kg – 15kg                                |
| FAC_FUNC_PULLUPBAR      | Pull-up Bar / Dip Station  | Lats, biceps, triceps, core               | 2        | Xà đơn + thanh chống đẩy                  |

---

### 3.5. Recovery & Stretching Area

| ID                      | Tên                        | Mục tiêu                                  | Notes                           |
|-------------------------|----------------------------|-------------------------------------------|---------------------------------|
| FAC_RECOV_FOAMROLLER    | Foam Rollers               | Myofascial release, recovery              | Khu vực giãn cơ                 |
| FAC_RECOV_STRETCHZONE   | Stretching Zone            | Flexibility, warmup/cooldown              | Thảm yoga + gương               |
| FAC_RECOV_MASSAGEGUN    | Massage Gun Station        | Deep tissue recovery                      | Thiết bị dùng chung có quản lý  |

---

## 4. Gợi Ý Relational Schema

### 4.1. `membership_tiers`

```sql
CREATE TABLE membership_tiers (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,  -- 'ESSENTIAL', 'STANDARD', 'PLUS', 'PREMIUM', 'ELITE'
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    priority_order  INT NOT NULL,                 -- sort thứ tự tier thấp → cao
    created_at      TIMESTAMP DEFAULT now(),
    updated_at      TIMESTAMP DEFAULT now()
);
```

### 4.2. `amenities`

```sql
CREATE TABLE amenities (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(50) UNIQUE NOT NULL,  -- 'POOL', 'SAUNA', 'TOWEL_SERVICE', 'PRIVATE_LOCKER', 'GROUP_CLASSES'
    name        VARCHAR(100) NOT NULL,
    description TEXT
);
```

### 4.3. `products`

```sql
CREATE TABLE products (
    id                     SERIAL PRIMARY KEY,
    code                   VARCHAR(20) UNIQUE NOT NULL,
    name                   VARCHAR(150) NOT NULL,
    tier_id                INT NOT NULL REFERENCES membership_tiers(id),
    billing_type           VARCHAR(30) NOT NULL,  -- 'monthly' | 'prepaid_quarterly' | 'prepaid_yearly'
    base_price_vnd         INT NOT NULL,          -- giá / tháng sau quy đổi
    commit_term_months     INT NOT NULL DEFAULT 0,
    pt_sessions_per_month  INT NOT NULL DEFAULT 0,
    guest_passes_per_month INT NOT NULL DEFAULT 0,
    spa_discount_percent   INT NOT NULL DEFAULT 0,
    is_most_popular        BOOLEAN NOT NULL DEFAULT FALSE,
    description            TEXT,
    created_at             TIMESTAMP DEFAULT now(),
    updated_at             TIMESTAMP DEFAULT now()
);
```

### 4.4. `product_amenities` (many-to-many)

```sql
CREATE TABLE product_amenities (
    product_id   INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    amenity_id   INT NOT NULL REFERENCES amenities(id) ON DELETE CASCADE,
    is_included  BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (product_id, amenity_id)
);
```

### 4.5. `facilities`

```sql
CREATE TABLE facilities (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50) UNIQUE NOT NULL,   -- 'FAC_CARDIO_TREADMILL'
    name          VARCHAR(150) NOT NULL,
    category      VARCHAR(30) NOT NULL,          -- 'cardio' | 'strength' | 'free_weights' | 'functional' | 'recovery'
    muscle_groups TEXT[],                         -- ['chest', 'triceps', 'anterior deltoid']
    aliases       TEXT[],                         -- ['máy tập ngực', 'chest press']
    description   TEXT,
    brand         VARCHAR(100),
    quantity      INT NOT NULL DEFAULT 1,
    available     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT now(),
    updated_at    TIMESTAMP DEFAULT now()
);
```

> `muscle_groups` và `aliases` là các field được **embed vào ChromaDB** (`gym_facilities` collection) để hỗ trợ semantic search. User hỏi "máy tập ngực" hay "máy leo cầu thang" đều match được đúng thiết bị mà không cần keyword chính xác.

### 4.6. Billing Plans (tuỳ chọn mở rộng)

```sql
CREATE TABLE billing_plans (
    id                 SERIAL PRIMARY KEY,
    product_id         INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    billing_type       VARCHAR(30) NOT NULL,
    commit_term_months INT NOT NULL,
    price_per_period   INT NOT NULL,   -- tổng tiền trả cho cả period
    equivalent_monthly INT NOT NULL,   -- để agent compare dễ
    currency           VARCHAR(10) NOT NULL DEFAULT 'VND'
);
```

---

## 5. Gợi Ý Query Cho Agent

```sql
-- Tìm gói dưới 1 triệu/tháng có pool + sauna
SELECT p.*
FROM products p
JOIN product_amenities pa1 ON pa1.product_id = p.id
JOIN amenities a1 ON a1.id = pa1.amenity_id AND a1.code = 'POOL'
JOIN product_amenities pa2 ON pa2.product_id = p.id
JOIN amenities a2 ON a2.id = pa2.amenity_id AND a2.code = 'SAUNA'
WHERE p.base_price_vnd <= 1000000
  AND pa1.is_included = TRUE
  AND pa2.is_included = TRUE;

-- Lấy gói phổ biến để agent recommend
SELECT * FROM products
WHERE is_most_popular = TRUE
ORDER BY base_price_vnd ASC;

-- Tìm thiết bị đang hoạt động theo category
SELECT * FROM facilities
WHERE category = 'cardio' AND available = TRUE
ORDER BY name;
```

---

## 6. Project Structure

```
gym-agent/
├── agent/
│   ├── graph.py           # LangGraph StateGraph definition + compile
│   ├── state.py           # AgentState TypedDict
│   ├── nodes.py           # tất cả node functions
│   ├── tools.py           # search_packages, get_detail, compare, book, search_facilities
│   └── router.py          # intent classification prompt
├── rag/
│   ├── ingest.py          # load policy docs → ChromaDB (gym_policy collection)
│   ├── ingest_facilities.py  # load facilities → ChromaDB (gym_facilities collection)
│   ├── retriever.py       # query rewrite + retrieve + rerank
│   └── grader.py          # self-grading node
├── guardrails/
│   ├── input_guard.py
│   └── output_guard.py
├── backend/
│   ├── main.py            # FastAPI mock server
│   ├── mock_data.py       # packages + facilities mock data
│   └── models.py          # Pydantic schemas
├── data/
│   └── policies/
├── .env.example
├── requirements.txt
└── README.md
```

---

## 7. Tech Stack

| Component        | Thư viện                        | Ghi chú                              |
|------------------|---------------------------------|--------------------------------------|
| Agent framework  | `langgraph`                     | StateGraph, conditional edges        |
| LLM              | `langchain-openai`              | GPT-4o-mini                          |
| Vector store     | `chromadb`                      | 2 collections: policy + facilities   |
| Reranking        | `sentence-transformers`         | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Mock server      | `fastapi` + `uvicorn`           | auto Swagger docs                    |
| Data validation  | `pydantic` v2                   |                                      |
| Observability    | `langsmith`                     | trace toàn bộ agent run              |
| Env management   | `python-dotenv`                 |                                      |
