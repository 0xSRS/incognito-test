import Link from "next/link";

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#0a0705",
        padding: "2rem",
        textAlign: "center",
      }}
    >
      <p
        style={{
          fontFamily:
            "'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Georgia, serif",
          fontSize: "0.8rem",
          letterSpacing: "0.3em",
          textTransform: "uppercase",
          color: "#8a6a34",
          marginBottom: "1.5rem",
        }}
      >
        File Not Found
      </p>

      <h1
        style={{
          fontFamily:
            "'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Georgia, serif",
          fontSize: "clamp(1.6rem, 4vw, 2.8rem)",
          color: "#e0b563",
          letterSpacing: "0.04em",
          lineHeight: 1.3,
          maxWidth: "640px",
          textShadow: "0 0 24px rgba(184,146,63,0.25)",
          marginBottom: "1.5rem",
        }}
      >
        This document has been removed from the archives.
      </h1>

      <div
        style={{
          width: "60px",
          height: "2px",
          background: "linear-gradient(90deg, transparent, #b8923f, transparent)",
          marginBottom: "1.5rem",
        }}
      />

      <p
        style={{
          fontFamily:
            "'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Georgia, serif",
          fontSize: "0.95rem",
          color: "#cabf9c",
          maxWidth: "480px",
          lineHeight: 1.7,
          marginBottom: "0.5rem",
        }}
      >
        The family destroys what it wishes forgotten&nbsp;—
      </p>
      <p
        style={{
          fontFamily: "'Italianno', cursive",
          fontSize: "1.4rem",
          color: "#b8923f",
          maxWidth: "480px",
          lineHeight: 1.6,
          fontStyle: "italic",
        }}
      >
        but nothing truly disappears. The past has a way of being&hellip; preserved.
      </p>

      <div style={{ marginTop: "2.5rem" }}>
        <Link
          href="/"
          style={{
            fontFamily:
              "'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Georgia, serif",
            fontSize: "0.75rem",
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: "#4a4128",
            textDecoration: "none",
            borderBottom: "1px solid rgba(184,146,63,0.22)",
            paddingBottom: "2px",
            transition: "color 0.3s, border-color 0.3s",
          }}
        >
          Return to the Family
        </Link>
      </div>
    </div>
  );
}
