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
  const [impact, setImpact] = useState({
    savings: 810,
    normalCost: 2375,
    optimizedCost: 1565,
    distanceSaved: 37.1,
    inputsReused: 10,
  });

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userText = input.trim();

    setMessages((previous) => [
      ...previous,
      {
        sender: "user",
        text: userText,
      },
    ]);

    setInput("");

    try {
      const response = await fetch("http://127.0.0.1:8000/ai/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          farmer_id: 1,
          message: userText,
        }),
      });

      if (!response.ok) {
        throw new Error("Backend error: " + response.status);
      }

      const data = await response.json();

      if (data.plan?.impact) {
        setImpact({
          savings: data.plan.impact.savings,
          normalCost: data.plan.impact.normal_cost,
          optimizedCost: data.plan.impact.optimized_cost,
          distanceSaved: data.plan.impact.distance_saved_km,
          inputsReused: data.plan.impact.input_reused_kg,
        });
      }

      const recommendation = data.recommendation;

      setMessages((previous) => [
        ...previous,
        {
          sender: "ai",
          text:
            recommendation?.summary?.join(" ") ||
            "Your farming request has been optimized successfully.",
        },
      ]);
    } catch (error) {
      console.error("Error connecting to KisanPool AI:", error);

      setMessages((previous) => [
        ...previous,
        {
          sender: "ai",
          text: "Sorry, I couldn't connect to the KisanPool AI backend. Please make sure the backend is running.",
        },
      ]);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      sendMessage();
    }
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          🌱 <span>KisanPool</span>
        </div>

        <nav>
          <button className="nav-item active">🏠 Dashboard</button>
          <button className="nav-item">💬 AI Assistant</button>
          <button className="nav-item">🚜 Resources</button>
          <button className="nav-item">📋 My Plans</button>
        </nav>

        <div className="sidebar-bottom">
          <div className="farmer-mini">
            <div className="avatar">👨‍🌾</div>
            <div>
              <strong>Farmer</strong>
              <small>My Farm</small>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">SMART FARMING PLATFORM</p>
            <h1>Good evening, Farmer 👋</h1>
            <p className="subtitle">
              Let's make your next farming decision smarter.
            </p>
          </div>

          <div className="profile">
            <span>🌾</span>
            <strong>My Farm</strong>
          </div>
        </header>

        {/* Stats */}
        <section className="stats">
          <div className="stat-card">
            <span className="stat-icon">💰</span>
            <div>
              <p>Money Saved</p>
              <h2>₹{impact.savings}</h2>
            </div>
          </div>

          <div className="stat-card">
            <span className="stat-icon">🚜</span>
            <div>
              <p>Resources Shared</p>
              <h2>3</h2>
            </div>
          </div>

          <div className="stat-card">
            <span className="stat-icon">🛣️</span>
            <div>
              <p>Travel Avoided</p>
              <h2>{impact.distanceSaved} km</h2>
            </div>
          </div>
        </section>

        {/* Dashboard */}
        <section className="dashboard-grid">
          {/* AI Assistant */}
          <div className="card assistant-card">
            <div className="card-header">
              <div>
                <p className="eyebrow">AI FARM ASSISTANT</p>
                <h2>What do you need today?</h2>
              </div>

              <span className="ai-status">● AI Online</span>
            </div>

            {/* Messages */}
            <div className="chat-window">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`message ${
                    message.sender === "user" ? "user-message" : "ai-message"
                  }`}
                >
                  {message.sender === "ai" && (
                    <span className="bot-icon">🤖</span>
                  )}

                  <div>
                    {message.sender === "ai" && <strong>KisanPool AI</strong>}

                    <p>{message.text}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Input */}
            <div className="chat-input">
              <input
                type="text"
                placeholder="Tell me what you need..."
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
              />

              <button onClick={sendMessage}>➤</button>
            </div>
          </div>

          {/* Impact */}
          <div className="card impact-card">
            <div className="card-header">
              <div>
                <p className="eyebrow">YOUR IMPACT</p>
                <h2>Latest optimized plan</h2>
              </div>
            </div>

            <div className="big-saving">
              ₹{impact.savings} <span>saved</span>
            </div>

            <div className="impact-row">
              <span>Normal cost</span>
              <strong>₹{impact.normalCost}</strong>
            </div>

            <div className="impact-row">
              <span>Optimized cost</span>
              <strong>₹{impact.optimizedCost}</strong>
            </div>

            <div className="impact-row">
              <span>Travel avoided</span>
              <strong>{impact.distanceSaved} km</strong>
            </div>

            <div className="impact-row">
              <span>Inputs reused</span>
              <strong>{impact.inputsReused} kg</strong>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
