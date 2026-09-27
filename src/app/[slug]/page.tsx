import { notFound } from "next/navigation";
import { pool } from "@/lib/db";

export const dynamic = "force-dynamic";

export default async function SlugPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;

  const directory = `incogito05.tech/${slug}`;

  const { rows } = await pool.query<{ flag: string }>(
    `SELECT uf.flag
       FROM pastes p
       JOIN user_flags uf ON uf.flag_id = p.flag_id
      WHERE p.directory = $1
        AND p.active = true`,
    [directory],
  );

  if (rows.length === 0) {
    notFound();
  }

  const flag = rows[0].flag;

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
      {/* decorative rule */}
      <div
        style={{
          width: "60px",
          height: "2px",
          background: "linear-gradient(90deg, transparent, #b8923f, transparent)",
          marginBottom: "2rem",
        }}
      />

      <p
        style={{
          fontFamily:
            "'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Georgia, serif",
          fontSize: "0.85rem",
          letterSpacing: "0.25em",
          textTransform: "uppercase",
          color: "#8a6a34",
          marginBottom: "1rem",
        }}
      >
        Classified — Eyes Only
      </p>

      <h1
        style={{
          fontFamily:
            "'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Georgia, serif",
          fontSize: "clamp(1.4rem, 4vw, 2.4rem)",
          color: "#e0b563",
          letterSpacing: "0.04em",
          lineHeight: 1.4,
          wordBreak: "break-all",
          maxWidth: "720px",
          textShadow: "0 0 24px rgba(184,146,63,0.25)",
        }}
      >
        {flag}
      </h1>

      {/* decorative rule */}
      <div
        style={{
          width: "60px",
          height: "2px",
          background: "linear-gradient(90deg, transparent, #b8923f, transparent)",
          marginTop: "2rem",
          marginBottom: "1.5rem",
        }}
      />

      <p
        style={{
          fontFamily:
            "'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Georgia, serif",
          fontSize: "0.8rem",
          color: "#4a4128",
          fontStyle: "italic",
        }}
      >
        This document will self‑destruct.
      </p>
    </div>
  );
}
