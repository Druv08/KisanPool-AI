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

  const sendMessage = () => {
    if (!input.trim()) return;

    const userMessage = {
      sender: "user",
      text: input,
    };

    setMessages((previous) => [
      ...previous,
      userMessage,
      {
        sender: "ai",
        text: "Got it! I'm processing your farming request.",
      },
    ]);

    setInput("");
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
              <h2>₹810</h2>
            </div>
          </div>

          <div className="stat-card">
            <span className="stat-icon">🚜</span>
            <div>
              <p>Resources Shared</p>
              <h2>4</h2>
            </div>
          </div>

          <div className="stat-card">
            <span className="stat-icon">🛣️</span>
            <div>
              <p>Travel Avoided</p>
              <h2>37.1 km</h2>
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
              ₹810
              <span>saved</span>
            </div>

            <div className="impact-row">
              <span>Normal cost</span>
              <strong>₹2375</strong>
            </div>

            <div className="impact-row">
              <span>Optimized cost</span>
              <strong>₹1565</strong>
            </div>

            <div className="impact-row">
              <span>Travel avoided</span>
              <strong>37.1 km</strong>
            </div>

            <div className="impact-row">
              <span>Inputs reused</span>
              <strong>10 kg</strong>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
