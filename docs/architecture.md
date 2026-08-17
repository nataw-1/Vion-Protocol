# Architecture

Visual diagrams of every VION Protocol subsystem.

---

## High-Level Architecture

```mermaid
graph TD
    Owner["👤 Owner<br/>(VION_AUTH_TOKEN)"] -->|OwnerCommand| ORC

    subgraph "Constitutional Layer"
        VM["📄 VION.md<br/>Supreme Law"]
        IM["📄 IDENTITY.md<br/>Agent Registry"]
        GS["📄 governance.state<br/>Suspension Persistence"]
    end

    subgraph "Governance Runtime"
        ORC["Orchestrator<br/>7-Stage Pipeline"]
        CV["ConstitutionValidator"]
        IR["IdentityRegistry"]
        HE["HALT Engine<br/>6 Conditions"]
        RC["Risk Cap Evaluator"]
        PD["Peer Detector"]
        NA["N Auditor<br/>Output Gate"]
        AL["Activity Logger<br/>Hash Chain"]
        TG["Telegram Reporter"]
    end

    subgraph "Agent Layer"
        A1["LangChain Agent"]
        A2["CrewAI Agent"]
        A3["Custom Agent"]
        A4["OpenAI Agent"]
    end

    VM -->|hash + parse| CV
    IM -->|parse| IR
    GS -->|suspensions| IR
    CV --> ORC
    IR --> ORC
    ORC --> HE
    ORC --> RC
    ORC --> PD
    ORC --> AL
    HE -->|alert| TG
    ORC -->|approved LIVE| A1
    ORC -->|approved LIVE| A2
    ORC -->|approved LIVE| A3
    ORC -->|approved LIVE| A4
    A1 -->|output| NA
    A2 -->|output| NA
    A3 -->|output| NA
    A4 -->|output| NA
    NA -->|pass| Owner
    NA -->|fail → C4| HE
    AL -->|log all events| Owner
```

---

## Orchestrator Pipeline

```mermaid
flowchart TD
    START(["OwnerCommand received"]) --> G0

    G0{"Guard 0\nConstitutional\nIntegrity Check"}
    G0 -->|VION.md or IDENTITY.md\nmodified mid-session| HALT6["🔴 HALT\nCondition 6\nImmediate"]
    G0 -->|Hashes match| G1

    G1{"Guard 1\nSystem HALTED?"}
    G1 -->|Yes| REJECT1["⛔ Reject\nSystemHaltedError"]
    G1 -->|No| S1

    S1{"Step 1\nAUTH Token\nValidation"}
    S1 -->|Invalid or missing| ESC1["🟡 ESCALATE → HALT\nCondition 1"]
    S1 -->|Valid| S2

    S2{"Step 2\nTimestamp\nValidation"}
    S2 -->|Expired > 300s| REJECT2["⛔ Reject\nExpired command"]
    S2 -->|Fresh| S3

    S3{"Step 3\nAgent Identity\nCheck"}
    S3 -->|Not found or suspended| ESC3["🟡 ESCALATE → HALT\nCondition 1"]
    S3 -->|Active| S4

    S4{"Step 4\nPeer-to-Peer\nDetection"}
    S4 -->|Peer command detected| ESC4["🟡 ESCALATE → HALT\nCondition 3"]
    S4 -->|Clean| S5

    S5{"Step 5\nScope\nValidation"}
    S5 -->|Out of scope| ESC5["🟡 ESCALATE → HALT\nCondition 2"]
    S5 -->|In scope| S6

    S6{"Step 6\nRisk Cap\nEvaluation"}
    S6 -->|Cap breached| ESC6["🟡 ESCALATE → HALT\nCondition 5"]
    S6 -->|Within caps| S7

    S7{"Step 7\nMode Resolution\nDRY_RUN or LIVE"}
    S7 -->|DRY_RUN| DRY["✅ Approved\nNot executed\nReturn result"]
    S7 -->|LIVE| EXEC

    EXEC["🤖 Agent Executes"]
    EXEC --> AUD

    AUD{"N Auditor\nOutput Gate\n6 Checks"}
    AUD -->|Output blocked| ESC7["🟡 ESCALATE → HALT\nCondition 4"]
    AUD -->|Output approved| DONE["✅ Deliver output\nto caller"]
```

---

## Identity System

```mermaid
stateDiagram-v2
    direction LR

    [*] --> Registered : Owner adds to IDENTITY.md

    state "Registered" as Registered {
        [*] --> ACTIVE : Owner activates
    }

    ACTIVE --> SUSPENDED : HALT Engine (violation)\nor Owner (manual)
    SUSPENDED --> ACTIVE : Owner reactivates\n+ governance.state updated
    ACTIVE --> TERMINATED : Owner terminates
    SUSPENDED --> TERMINATED : Owner terminates
    TERMINATED --> [*]

    note right of SUSPENDED
        Written to governance.state
        Persists across restarts
    end note

    note right of TERMINATED
        Permanent.
        Cannot be reactivated.
    end note
```

---

## Audit Log — Hash Chain

```mermaid
graph LR
    G["GENESIS\nSHA-256\n(N-VION-GENESIS)"]

    E1["Entry 1\ncontent: system_start\nprev: GENESIS_HASH\nhash: SHA256(content+prev)"]
    E2["Entry 2\ncontent: command_received\nprev: E1.hash\nhash: SHA256(content+prev)"]
    E3["Entry 3\ncontent: task_dispatched\nprev: E2.hash\nhash: SHA256(content+prev)"]
    EN["Entry N\ncontent: ...\nprev: E(N-1).hash\nhash: SHA256(content+prev)"]

    G -->|prev_hash| E1
    E1 -->|prev_hash| E2
    E2 -->|prev_hash| E3
    E3 -->|...| EN

    TAMPER["❌ Tamper\nEntry 2"]
    TAMPER -.->|Changes E2.hash| BREAK["🔴 Chain broken\nat Entry 3\nverify_chain() detects"]
    E2 -.-> TAMPER
```

---

## Multi-Agent Governance

```mermaid
graph TD
    Owner["👤 Owner"] -->|Single AUTH token| ORC["Orchestrator\n(Shared Instance)"]

    ORC -->|VION-RSC-001\napproved| RA["🔵 Research Agent\nScope: web sources\nCaps: no financial"]
    ORC -->|VION-EXC-001\napproved + override| EA["🟠 Execution Agent\nScope: file system\nCaps: no bulk ops\nDRY_RUN: OVERRIDE_REQUIRED"]
    ORC -->|VION-MON-001\napproved| MA["🟢 Monitor Agent\nScope: logs only\nCaps: read-only"]

    ORC -->|Shared| LOG["📋 Activity Log\nAll agents\nSame session"]
    ORC -->|Shared| HALT["🛑 HALT Engine\nOne HALT stops ALL agents"]
    ORC -->|Shared| TG["📱 Telegram\nOwner alerts"]

    RA -.->|BLOCKED: peer comms| EA
    RA -.->|BLOCKED: peer comms| MA
    EA -.->|BLOCKED: peer comms| MA

    note["Note: Agents cannot\ncommunicate directly.\nAll tasks route through\nthe Orchestrator only."]
```

---

## HALT Condition Response Matrix

```mermaid
graph LR
    subgraph "Condition 1 — Unauthorized Source"
        C1_1["1st-2nd: ESCALATE\nSuspend agent\nTelegram alert"] --> C1_2["3rd: HALT\nAll agents suspended\nFull shutdown"]
    end

    subgraph "Condition 2 — Scope Violation"
        C2_1["1st: ESCALATE"] --> C2_2["2nd: HALT"]
    end

    subgraph "Condition 3 — Peer Communication"
        C3_1["1st: ESCALATE"] --> C3_2["2nd: HALT"]
    end

    subgraph "Condition 4 — Output Audit Failure"
        C4_1["1st-2nd: ESCALATE"] --> C4_2["3rd: HALT"]
    end

    subgraph "Condition 5 — Risk Cap Breach"
        C5_1["ESCALATE\nBelow 2x cap"] --> C5_2["HALT\nAt or above 2x cap"]
    end

    subgraph "Condition 6 — Constitutional Integrity"
        C6["HALT IMMEDIATELY\nNo escalation\nNo exceptions"]
    end
```
