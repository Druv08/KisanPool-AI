import { useState } from "react";
import "./App.css";

function App() {
  const [messages, setMessages] = useState([
    {
      sender: "ai",
      text: "Hello! I'm KisanPool AI. Tell me what you need for your farm.",
    },
  ]);

  const [input, setInput] = useState("");
  const [plan, setPlan] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [farmerId, setFarmerId] = useState(1);
  const [loading, setLoading] = useState(false);
  const [bookingConfirmed, setBookingConfirmed] = useState(false);
  const [pendingRequest, setPendingRequest] = useState("");

  const [impact, setImpact] = useState({
    savings: 0,
    normalCost: 0,
    optimizedCost: 0,
    distanceSaved: 0,
    solarHours: 0,
    inputsReused: 0,
  });

  const sendMessage = async () => {
    const userText = input.trim();

    if (!userText || loading) return;

    const requestToSend = pendingRequest
      ? `${pendingRequest} for ${userText}`
      : userText;

    setMessages((previous) => [
      ...previous,
      {
        sender: "user",
        text: userText,
      },
    ]);

    setInput("");
    setLoading(true);
    setBookingConfirmed(false);

    try {
      console.log("ORIGINAL REQUEST:", pendingRequest);
      console.log("CURRENT ANSWER:", userText);
      console.log("REQUEST SENT TO BACKEND:", requestToSend);

      const response = await fetch("http://127.0.0.1:8000/plan", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          farmer_id: farmerId,
          message: requestToSend,
        }),
      });

      const data = await response.json();

      console.log("PLAN RESPONSE:", data);

      /* --------------------------------
   MISSING INFORMATION
-------------------------------- */

      if (
        data.status === "needs_information" ||
        (response.status === 400 && data.detail)
      ) {
        setPendingRequest((previous) => previous || userText);

        const questions = Array.isArray(data.questions)
          ? data.questions
          : data.detail
            ? [data.detail]
            : [];

        setMessages((previous) => [
          ...previous,
          {
            sender: "ai",
            text:
              "I need a little more information:\n\n" +
              questions.map((question) => `• ${question}`).join("\n"),
          },
        ]);

        setPage("create");
        return;
      }

      /* --------------------------------
   API ERRORS
-------------------------------- */

      if (!response.ok) {
        let errorMessage = "I couldn't create your farm plan.";

        if (response.status === 404) {
          errorMessage =
            "I couldn't find that farmer. Please select a valid farmer.";
        } else if (response.status === 422) {
          errorMessage =
            "I couldn't understand the request. Please provide a little more detail.";
        } else if (response.status >= 500) {
          errorMessage =
            "The planning service is temporarily unavailable. Please try again.";
        } else if (data.detail) {
          errorMessage = data.detail;
        }

        setMessages((previous) => [
          ...previous,
          {
            sender: "ai",
            text: "I couldn't create an optimized plan for this request.",
          },
        ]);

        setPage("create");
        return;
      }

      /* --------------------------------
       SAVE PLAN
    -------------------------------- */

      setPlan(data);

      setPendingRequest("");

      /* --------------------------------
       SAVE IMPACT
    -------------------------------- */

      if (data.impact) {
        setImpact({
          savings: data.impact.savings ?? 0,
          normalCost: data.impact.normal_cost ?? 0,
          optimizedCost: data.impact.optimized_cost ?? 0,
          distanceSaved: data.impact.distance_saved_km ?? 0,
          solarHours: data.impact.solar_hours ?? 0,
          inputsReused: data.impact.input_reused_kg ?? 0,
        });
      }

      /* --------------------------------
       AI MESSAGE
    -------------------------------- */

      let resultMessage = "Your optimized farm plan is ready. ";

      if (data.machinery) {
        resultMessage +=
          `🚜 ${data.machinery.name} from ${data.machinery.owner} ` +
          `is scheduled for ${data.machinery.start}–${data.machinery.end}. `;
      } else {
        resultMessage +=
          "⚠️ No suitable machinery was found for this request. ";
      }

      if (data.irrigation && data.irrigation.status !== "not_requested") {
        resultMessage += `☀️ ${data.irrigation.name} has been selected for irrigation. `;
      }

      const inputs = Array.isArray(data.inputs) ? data.inputs : [];

      if (inputs.length > 0) {
        resultMessage += `🌱 ${inputs.length} shared input supplier(s) found. `;
      }

      if (data.impact?.savings !== undefined) {
        resultMessage += `Estimated savings: ₹${data.impact.savings}.`;
      }

      setMessages((previous) => [
        ...previous,
        {
          sender: "ai",
          text: resultMessage,
        },
      ]);

      /* --------------------------------
       SHOW AI PLAN
    -------------------------------- */

      setPage("dashboard");
    } catch (error) {
      console.error("KisanPool API error:", error);

      setMessages((previous) => [
        ...previous,
        {
          sender: "ai",
          text:
            "I couldn't create your farm plan right now. " +
            "Please make sure the backend is running and try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const confirmPlan = () => {
    setBookingConfirmed(true);
  };

  const startNewPlan = () => {
    setPlan(null);
    setInput("");
    setPendingRequest("");
    setBookingConfirmed(false);

    setImpact({
      savings: 0,
      normalCost: 0,
      optimizedCost: 0,
      distanceSaved: 0,
      solarHours: 0,
      inputsReused: 0,
    });

    setPage("create");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app">
      {/* =========================================
          SIDEBAR
      ========================================= */}

      <aside className="sidebar">
        <div className="logo">
          <div className="logo-mark">🌱</div>
          <div>
            <strong>KisanPool</strong>
            <span>AI</span>
          </div>
        </div>

        <div className="sidebar-section-title">WORKSPACE</div>

        <nav>
          <button
            className={`nav-item ${page === "dashboard" ? "active" : ""}`}
            onClick={() => setPage("dashboard")}
          >
            <span>⌂</span>
            Dashboard
          </button>

          <button
            className={`nav-item ${page === "create" ? "active" : ""}`}
            onClick={() => setPage("create")}
          >
            <span>✦</span>
            AI Assistant
          </button>

          <button
            className="nav-item"
            onClick={() => {
              setPage("dashboard");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          >
            <span>🚜</span>
            Resources
          </button>

          <button className="nav-item" onClick={() => setPage("dashboard")}>
            <span>▣</span>
            My Plans
          </button>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <div className="help-icon">?</div>
            <div>
              <strong>Need help?</strong>
              <span>Ask KisanPool AI</span>
            </div>
          </div>

          <div className="sidebar-user">
            <div className="avatar">R</div>

            <div className="user-info">
              <strong>Ravi Kumar</strong>
              <span>Farmer</span>
            </div>

            <span className="user-menu">•••</span>
          </div>
        </div>
      </aside>

      {/* =========================================
          MAIN
      ========================================= */}

      <main className="main">
        {/* =====================================
            CREATE PLAN PAGE
        ===================================== */}

        {page === "create" && (
          <section className="create-page">
            <div className="create-container">
              <button
                className="page-back"
                onClick={() => setPage("dashboard")}
              >
                ← Dashboard
              </button>

              <div className="create-hero">
                <div className="ai-badge">
                  <span>✦</span>
                  KISANPOOL AI
                </div>

                <h1>
                  Plan your next
                  <br />
                  <span>farming activity.</span>
                </h1>

                <p>
                  Tell KisanPool AI what you need in your own words. We'll find
                  the best available resources for your farm.
                </p>
              </div>

              <div className="create-card">
                <div className="form-group">
                  <label>FARMER</label>

                  <select
                    value={farmerId}
                    onChange={(event) =>
                      setFarmerId(Number(event.target.value))
                    }
                  >
                    <option value={1}>Ravi Kumar — My Farm</option>

                    <option value={2}>Farmer 2</option>

                    <option value={3}>Farmer 3</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>WHAT DO YOU NEED?</label>

                  <textarea
                    value={input}
                    onChange={(event) => setInput(event.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      messages.length > 1
                        ? "Answer the AI's question or describe anything else you need..."
                        : "Example: I need a tractor, irrigation and 10kg tomato seeds tomorrow for my 2 acre farm"
                    }
                    rows={6}
                  />

                  <div className="input-hint">
                    <span>✦</span>
                    Describe your requirement naturally
                  </div>
                </div>

                <button
                  className="create-plan-button"
                  onClick={sendMessage}
                  disabled={loading || !input.trim()}
                >
                  {loading ? (
                    <>
                      <span className="spinner"></span>
                      Finding the best resources...
                    </>
                  ) : (
                    <>
                      Create AI Plan
                      <span>→</span>
                    </>
                  )}
                </button>
              </div>

              <div className="example-area">
                <span>TRY AN EXAMPLE</span>

                <button
                  onClick={() =>
                    setInput("I need a tractor tomorrow for tomato on 2 acres")
                  }
                >
                  🚜 Tractor for 2 acres
                </button>

                <button
                  onClick={() =>
                    setInput(
                      "I need a tractor, irrigation and 10kg tomato seeds tomorrow for my 2 acre farm",
                    )
                  }
                >
                  🌱 Complete farm plan
                </button>
              </div>

              {messages.length > 1 && (
                <div className="chat-preview">
                  <div className="chat-preview-title">AI Assistant</div>

                  {messages.slice(-3).map((message, index) => (
                    <div
                      className={`chat-message ${message.sender}`}
                      key={index}
                    >
                      <span>{message.text}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {/* =====================================
            DASHBOARD
        ===================================== */}

        {page === "dashboard" && (
          <>
            <header className="topbar">
              <div>
                <p className="eyebrow">FARM OVERVIEW</p>

                <h1>
                  Good morning, Ravi <span>👋</span>
                </h1>

                <p className="topbar-subtitle">
                  Here's what's happening with your farm today.
                </p>
              </div>

              <button
                className="primary-button"
                onClick={() => setPage("create")}
              >
                <span>+</span>
                Create Farm Plan
              </button>
            </header>

            {/* =================================
                KPI CARDS
            ================================= */}

            <section className="stats-grid">
              <div className="card stat-card">
                <div className="stat-top">
                  <span className="stat-label">ESTIMATED SAVINGS</span>

                  <div className="stat-icon">₹</div>
                </div>

                <h2>₹{impact.savings.toLocaleString("en-IN")}</h2>

                <p>
                  <span className="positive">↗</span>
                  From optimized resource pooling
                </p>
              </div>

              <div className="card stat-card">
                <div className="stat-top">
                  <span className="stat-label">TRAVEL AVOIDED</span>

                  <div className="stat-icon">⌖</div>
                </div>

                <h2>{impact.distanceSaved} km</h2>

                <p>Estimated sourcing distance</p>
              </div>

              <div className="card stat-card">
                <div className="stat-top">
                  <span className="stat-label">SOLAR IRRIGATION</span>

                  <div className="stat-icon">☀</div>
                </div>

                <h2>{impact.solarHours} hrs</h2>

                <p>Renewable irrigation usage</p>
              </div>

              <div className="card stat-card">
                <div className="stat-top">
                  <span className="stat-label">INPUTS SHARED</span>

                  <div className="stat-icon">♧</div>
                </div>

                <h2>{impact.inputsReused} kg</h2>

                <p>Community resources reused</p>
              </div>
            </section>

            {/* =================================
                DASHBOARD CONTENT
            ================================= */}

            <section className="dashboard-grid">
              <div className="card activity-card">
                <div className="card-header">
                  <div>
                    <p className="eyebrow">QUICK ACTION</p>

                    <h2>What are you working on?</h2>
                  </div>

                  <div className="card-header-icon">✦</div>
                </div>

                <p className="card-description">
                  Describe your farming requirement and KisanPool AI will match
                  you with nearby resources.
                </p>

                <button
                  className="secondary-action"
                  onClick={() => setPage("create")}
                >
                  Start planning
                  <span>→</span>
                </button>
              </div>

              <div className="card impact-card">
                <div className="card-header">
                  <div>
                    <p className="eyebrow">RESOURCE POOLING</p>

                    <h2>Cost impact</h2>
                  </div>
                </div>

                <div className="impact-row">
                  <span>Normal estimated cost</span>

                  <strong>₹{impact.normalCost.toLocaleString("en-IN")}</strong>
                </div>

                <div className="impact-row">
                  <span>Optimized cost</span>

                  <strong>
                    ₹{impact.optimizedCost.toLocaleString("en-IN")}
                  </strong>
                </div>

                <div className="impact-row highlight-row">
                  <span>You save</span>

                  <strong>₹{impact.savings.toLocaleString("en-IN")}</strong>
                </div>
              </div>
            </section>

            {/* =================================
                AI PLAN
            ================================= */}

            {plan && (
              <section className="plan-section">
                <div className="plan-card card">
                  {/* PLAN HEADER */}

                  <div className="plan-header">
                    <div>
                      <div className="ai-badge small">
                        <span>✦</span>
                        AI OPTIMIZED
                      </div>

                      <h2>Your recommended farm plan</h2>

                      <p>
                        KisanPool AI found the best available resources for your
                        request.
                      </p>
                    </div>

                    <span className="plan-id">PLAN #{plan.plan_id}</span>
                  </div>

                  {/* MACHINERY */}

                  <div className="resource-block">
                    <div className="resource-icon machinery">🚜</div>

                    <div className="resource-content">
                      <div className="resource-title-row">
                        <div>
                          <span className="resource-type">MACHINERY</span>

                          <h3>
                            {plan.machinery
                              ? plan.machinery.name
                              : "No machinery available"}
                          </h3>
                        </div>

                        {plan.machinery && (
                          <strong className="resource-price">
                            ₹{plan.machinery.cost.toLocaleString("en-IN")}
                          </strong>
                        )}
                      </div>

                      {plan.machinery ? (
                        <>
                          <p className="resource-provider">
                            Provided by <strong>{plan.machinery.owner}</strong>
                          </p>

                          <div className="resource-meta">
                            <span>📍 {plan.machinery.distance_km} km</span>

                            <span>
                              🕘 {plan.machinery.start} – {plan.machinery.end}
                            </span>

                            <span className="available">● Available</span>
                          </div>
                        </>
                      ) : (
                        <div className="warning-message">
                          No suitable machinery was found for this request.
                        </div>
                      )}
                    </div>
                  </div>

                  {/* IRRIGATION */}

                  {plan.irrigation &&
                    plan.irrigation.status !== "not_requested" && (
                      <div className="resource-block">
                        <div className="resource-icon solar">☀️</div>

                        <div className="resource-content">
                          <div className="resource-title-row">
                            <div>
                              <span className="resource-type">
                                SOLAR IRRIGATION
                              </span>

                              <h3>{plan.irrigation.name}</h3>
                            </div>

                            <strong className="resource-price">
                              ₹{plan.irrigation.cost.toLocaleString("en-IN")}
                            </strong>
                          </div>

                          <p className="resource-provider">
                            Provided by <strong>{plan.irrigation.owner}</strong>
                          </p>

                          <div className="resource-meta">
                            <span>📍 {plan.irrigation.distance_km} km</span>

                            <span>
                              🕘 {plan.irrigation.start} – {plan.irrigation.end}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                  {/* INPUTS */}

                  {plan.inputs && plan.inputs.length > 0 && (
                    <div className="inputs-section">
                      <div className="section-heading">
                        <div>
                          <span className="resource-type">
                            SHARED FARM INPUTS
                          </span>

                          <h3>Community input pool</h3>
                        </div>

                        <span className="shared-badge">
                          {plan.inputs.length} supplier
                          {plan.inputs.length !== 1 ? "s" : ""}
                        </span>
                      </div>

                      <div className="input-list">
                        {plan.inputs.map((item, index) => (
                          <div className="input-row" key={index}>
                            <div className="input-name">
                              <div className="input-icon">🌱</div>

                              <div>
                                <strong>{item.item}</strong>

                                <span>
                                  {item.quantity} {item.unit} required
                                </span>
                              </div>
                            </div>

                            <div className="input-provider">
                              <span>Supplier</span>

                              <strong>{item.owner}</strong>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* IMPACT */}

                  {plan.impact && (
                    <div className="plan-impact">
                      <div className="impact-heading">
                        <div>
                          <span className="resource-type">
                            SUSTAINABILITY & IMPACT
                          </span>

                          <h3>The difference your plan makes</h3>
                        </div>
                      </div>

                      <div className="impact-grid">
                        <div className="impact-metric">
                          <span className="metric-icon">₹</span>

                          <strong>
                            ₹{plan.impact.savings.toLocaleString("en-IN")}
                          </strong>

                          <span>Estimated savings</span>
                        </div>

                        <div className="impact-metric">
                          <span className="metric-icon">⌖</span>

                          <strong>{plan.impact.distance_saved_km} km</strong>

                          <span>Travel avoided</span>
                        </div>

                        <div className="impact-metric">
                          <span className="metric-icon">☀</span>

                          <strong>{plan.impact.solar_hours} hrs</strong>

                          <span>Solar irrigation</span>
                        </div>

                        <div className="impact-metric">
                          <span className="metric-icon">♧</span>

                          <strong>{plan.impact.input_reused_kg} kg</strong>

                          <span>Inputs shared</span>
                        </div>
                      </div>

                      <p className="impact-note">
                        Impact values are estimates based on current plan
                        assumptions.
                      </p>
                    </div>
                  )}

                  {/* RECOMMENDATION */}

                  <div className="recommendation">
                    <div className="recommendation-icon">✦</div>

                    <div>
                      <span className="resource-type">
                        KISANPOOL AI RECOMMENDATION
                      </span>

                      <p>
                        {plan.recommendation?.summary?.join(" ") ||
                          "This plan was optimized using available resources, cost and distance."}
                      </p>
                    </div>
                  </div>

                  {/* ACTION */}

                  <div className="plan-actions">
                    {!bookingConfirmed ? (
                      <>
                        <button
                          className="confirm-button"
                          onClick={confirmPlan}
                        >
                          ✓ Confirm Plan
                        </button>

                        <button
                          className="secondary-action"
                          onClick={startNewPlan}
                        >
                          Find another plan
                        </button>
                      </>
                    ) : (
                      <div className="booking-success">
                        <span>✓</span>

                        <div>
                          <strong>Booking confirmed</strong>

                          <p>Your resource plan has been saved successfully.</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
