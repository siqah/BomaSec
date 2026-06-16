export default function Home() {
  return (
    <main
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <div
        style={{
          width: "64px",
          height: "64px",
          borderRadius: "16px",
          background: "linear-gradient(135deg, #6366f1, #22d3ee)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "28px",
        }}
      >
        🛡️
      </div>
      <h1
        style={{
          fontSize: "2rem",
          fontWeight: 700,
          background: "linear-gradient(135deg, #6366f1, #22d3ee)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        BomaSec
      </h1>
      <p style={{ color: "#71717a", fontSize: "0.95rem" }}>
        SOC-in-a-Box — Phase 1 Environment Ready
      </p>
    </main>
  );
}
