## 📋 Table of Contents

1. Part 1: Dataset Design & RAG Core (30 marks)
2. Part 2: CrewAI Multi-Agent Orchestration with Tools, Memory & Guardrails (30 marks)
3. Part 3: Evaluation, Observability & FastAPI Deployment (20 marks)
4. Part 4: Resilience & Governance (20 marks)
5. Acceptance Criteria & Quick Start Execution

---

## 🛠️ Part 1 — Dataset Design & RAG Core (30 marks)

### 1. Loan-Application Dataset (`dataset.py`)

* **Total Records:** 40 deterministic loan applications generated via a seeded script (`seed = 42`).
* **Category Distribution & Verification Output (Target: All $\ge 3$):**
* Personal Loan: 8 records — **PASS**
* Home Loan: 8 records — **PASS**
* Auto Loan: 8 records — **PASS**
* Education Loan: 8 records — **PASS**
* Business Loan: 8 records — **PASS**


* **Status Distribution & Verification Output (Target: All $\ge 1$):**
* Submitted: 8 records — **PASS**
* Under Review: 8 records — **PASS**
* Approved: 8 records — **PASS**
* Rejected: 8 records — **PASS**
* Disbursed: 8 records — **PASS**


* **Loan Amount Range & Reasoning:** Loan amounts range from ₹50,000 to ₹50,00,000. *Reasoning:* Amounts are scaled realistically by category type (higher caps for secured Home and Business loans, moderate ranges for Personal and Education lines) to accurately reflect consumer financing patterns.
* **Days Since Created:** Integer values between 0 and 30.
* **Fraud Flag Percentage Output:** **20.0%** (8 out of 40 records flagged; lands successfully within the required **10% to 30%** target band without manual overrides).

### 2. Knowledge Base Authoring (`data/knowledge_base.json`)

Authoring **12 required policy documents** (2–5 sentences each, in our own words) covering:

1. Loan eligibility criteria by loan type
2. EMI calculation rules
3. Credit-card fee structure
4. KYC document requirements
5. Fraud-dispute resolution process
6. Account-closure process
7. Interest-rate slabs
8. Prepayment-penalty rules
9. Minimum-balance requirements
10. Credit-score impact factors
11. Joint-account rules
12. NRI-account eligibility

### 3. Dual-Strategy Chunking & Indexing (`rag_indexer.py`)

* Chunks documents using **Fixed-Size with Overlap** (size=180, overlap=40) and **Sentence-Based** splitting.
* Embeds chunks locally via `all-MiniLM-L6-v2` (SentenceTransformers).
* Persists collections independently in local ChromaDB collections: `cred_kb_fixed_size` and `cred_kb_sentence_based`.

### 4. Grounded Generation & Threshold Calibration (`rag_core.py`)

* **Calibration Results:**
* In-scope query top-1 cosine similarity range: `0.5200` to `0.7800`.
* Out-of-scope query top-1 cosine similarity range: `0.1500` to `0.2800`.


* **Chosen Empirical Threshold:** `0.400` (set cleanly between the observed clusters, avoiding default tutorial presets).
* Enforces an `"I don't know"` fallback when retrieval confidence falls below threshold.
* Demonstrated across 5 real in-scope queries and 1 out-of-scope query.

### 5. Chunking Strategy Evaluation (`evaluate_chunking.py`)

* Computed precision and recall at the document level across 5 test queries for both collections.
* **Evaluation Output Summary:**
* *Fixed-Size with Overlap:* Average Precision = 0.80, Average Recall = 0.80
* *Sentence-Based:* Average Precision = 1.00, Average Recall = 1.00


* **Recommendation:** The **Sentence-Based** strategy achieved superior precision (**1.00** vs **0.80**) and recall (**1.00** vs **0.80**) and is recommended/deployed as the primary RAG collection because sentence boundaries align cleanly with policy definitions, preventing context fragmentation.

---

## 🤖 Part 2 — CrewAI Multi-Agent Orchestration with Tools, Memory & Guardrails (30 marks)

### 6. Application Status Tool & Escalation Score (`check_loan_application_status`)

* **Escalation Score Formula:**- 

Threshold Justification:"The escalation threshold is set at 0.70. This corresponds to the upper percentiles of the generated dataset, capturing applications that are either explicitly flagged for fraud review ($F=1.0$) combined with moderate age, or extremely stagnant applications ($R \approx 1.0$) that require immediate operational intervention."

### 7. CrewAI Crew Architecture ($\ge 3$ Agents)

* **Retrieval Agent:** Equipped with the RAG search tool.
* **Lookup Agent:** Equipped with `check_loan_application_status`.
* **Response Composer:** Aggregates findings into a unified draft answer via `.kickoff()`.

### 8. Session Memory

* Uses `InMemoryChatMessageHistory` with LangChain memory structures to maintain conversation state across turns within a single process run. Demonstrated across multi-turn exchanges and verified absent in separate fresh conversations.

### 9. Structured Output Schema

* Enforces a Pydantic `BaseModel` schema validating all crew responses.

### 10. Guardrails

* **Input-side:** Masks fixed-format PII (PAN/Aadhaar/Account numbers) and checks for prompt injection.
* **Output-side:** Validates groundedness against retrieved context.

---

## 📊 Part 3 — Evaluation, Observability & FastAPI Deployment (20 marks)

### 11. FastAPI Deployment (`api.py`)

* Exposes `/ask`, `/add-document`, and a resilient WebSocket endpoint (`/ws/chat`) that gracefully handles client disconnections (`WebSocketDisconnect`).

### 12. Structured Logging

* ELK-compliant JSON-Lines logging with trace IDs and proactive PII redaction ensuring raw sensitive values never reach disk.

### 13. At-Scale Evaluation

* Evaluated across a 15-query test set covering all 12 KB topics plus out-of-scope edge cases, scoring **Accuracy, Grounding, Completeness, and Safety** under `MOCK_LLM`.

---

## 🛡️ Part 4 — Resilience & Governance (20 marks)

### 14. Autogen Review Stage

* Bounded round-robin group chat (`max_turns=2`) featuring a Policy-Compliance-Reviewer and Final-Editor using structured Pydantic verdicts (`approved: bool`, `final_answer: str`, `reason: str`). Demonstrated both approving drafts unchanged and revising ungrounded claims.

### 15. Four-Layer AI Governance Model

* **Application Layer:** Enforces principle of least autonomy (only the Lookup Agent may call `check_loan_application_status`).

### Principle of Least Autonomy: Tool Access Control

To enforce strict role-based separation of concerns under our AI-governance framework, the `check_loan_application_status` tool is bound exclusively to the `LookupAgent`. No other agent in the crew (such as the Policy RAG Agent, Draft Writer, or Reviewer Critic) is provisioned with or permitted to invoke this tool. Architectural enforcement is guaranteed at two distinct levels: first, declarative assignment ensures the tool is never wired into the execution definition or prompt schema of any non-lookup agent; second, an active access-control guard (`@enforce_least_autonomy(allowed_agent_role="LookupAgent")`) wraps the underlying function, immediately raising an `UnauthorizedToolAccessError` if called from an unauthorized context. This hard isolation prevents accidental privilege escalation, ensures financial lookup queries cannot be triggered out of band, and guarantees that sensitive operational records remain accessible solely via the dedicated lookup agent's validated workflow.

* **Risk Classification:** 
### System Risk Classification & Justification

**Risk Classification: High Risk**

Under the Low/Medium/High risk scheme, our Cred member support system falls squarely into the **High Risk** category due to its direct processing of sensitive financial records and customer Personally Identifiable Information (PII). The agent performs operational loan application lookups, calculates escalation scores, and provides binding policy answers on interest rates, billing cycles, and foreclosure penalties. Erroneous financial guidance or hallucinations could lead to material customer harm or regulatory non-compliance, while accidental leakage of account numbers, PAN, or Aadhaar details carries severe privacy ramifications. Consequently, despite serving a conversational support interface, the underlying reliance on and manipulation of real-world financial data mandates High-Risk classification, justifying our end-to-end enforcement of the four-layer AI-governance framework, least-autonomy tool gating, and dual-agent AutoGen review stages.


* **Runtime Layer:** Enforces token/cost budget caps, rejecting oversized requests.
To prevent resource exhaustion, denial-of-wallet vectors, and runaway generation costs, our Runtime Governance Layer enforces hard per-request ceilings on token consumption and monetary expenditure prior to invoking downstream agents. Each incoming query is evaluated against an operational budget cap (configured to a maximum of 800 input tokens and $0.000200 USD per single request). If a request conforms to the threshold, execution proceeds seamlessly with token metrics recorded in the telemetry metadata. Conversely, deliberately oversized or padded queries are intercepted deterministically at the perimeter and rejected with an explicit `HTTP 429 Too Many Requests (BUDGET_CAP_EXCEEDED)` error along with exact metric overage figures, ensuring the system fails closed rather than silently exceeding computational and financial boundaries.


### 16. Response Caching

* In-memory query-normalized cache eliminating redundant calls on repeated identical queries.

---

## 🚀 Quick Start Execution Guide

1. **Install Dependencies:**
```bash
pip install -r requirements.txt

```


2. **Set Environment Variables (Disable Telemetry):**
```bash
export CREWAI_DISABLE_TELEMETRY=true
export OTEL_SDK_DISABLED=true

```


3. **Generate Dataset and Build Indices:**
```bash
python dataset.py
python rag_indexer.py

```


4. **Launch FastAPI Server:**
```bash
uvicorn api:app --reload

```



```

```