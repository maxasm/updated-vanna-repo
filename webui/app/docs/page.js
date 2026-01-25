import React from "react";

export default function DocsPage() {
  return (
    <main style={{ maxWidth: 900, margin: "0 auto", padding: "2rem" }}>
      <header style={{ borderBottom: "2px solid var(--foreground)", marginBottom: "2rem", opacity: 0.2 }}>
        <h1 style={{ fontSize: "2.5rem", fontWeight: 700, marginBottom: "0.5rem" }}>
          API Documentation
        </h1>
        <p style={{ color: "var(--foreground)", fontSize: "1.2rem", marginBottom: "1rem", opacity: 0.7 }}>
          Official reference for the Vanna AI backend REST API.
        </p>
        <p>
          <strong>Backend:</strong> Python (FastAPI) &nbsp;|&nbsp; <strong>Version:</strong> v1/v2
        </p>
      </header>

      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1rem" }}>Overview</h2>
        <p>
          This API provides endpoints for chat, learning, conversation management, database inspection, and more.
          All endpoints return JSON unless otherwise specified.
        </p>
        <p>
          <strong>Base URL:</strong> <code>/</code> (relative to your deployment)
        </p>
      </section>

      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1rem" }}>Authentication</h2>
        <p>
          Most endpoints expect user identification via HTTP headers:
        </p>
        <ul>
          <li><code>x-user-id</code> or <code>x-user-identifier</code> (string, optional)</li>
          <li><code>x-username</code> (string, optional)</li>
          <li><code>x-user-groups</code> (comma-separated, optional)</li>
        </ul>
        <p>
          If not provided, defaults are used. Some endpoints may require additional context.
        </p>
      </section>

      <section style={{ marginBottom: "2.5rem" }}>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1rem" }}>Endpoints</h2>
        <Endpoint
          method="POST"
          path="/api/v1/chat"
          summary="Chat with the agent"
          description="Send a message to the agent and receive a response, SQL query, and CSV link."
          requestBody={{
            message: "string (required) - The user's message/question.",
            headers: "object (optional) - User/session headers."
          }}
          response={{
            answer: "string - Agent's response.",
            sql: "string - SQL query generated.",
            csv_url: "string - Link to CSV file with results.",
            chart: "object|null - Chart data if generated.",
            success: "boolean",
            timestamp: "string (ISO8601)",
            tool_used: "boolean",
            user_id: "string",
            conversation_id: "string|null",
            username: "string"
          }}
        />

        <Endpoint
          method="GET"
          path="/api/v1/learning/stats"
          summary="Get learning statistics"
          description="Returns statistics about the agent's learning patterns and usage."
        />

        <Endpoint
          method="GET"
          path="/api/v1/health"
          summary="Health check"
          description="Returns service health status."
        />

        <Endpoint
          method="POST"
          path="/api/v1/train"
          summary="Train agent with schema"
          description="Triggers agent training on the database schema."
        />

        <Endpoint
          method="POST"
          path="/api/vanna/v2/chat_sse"
          summary="Chat (SSE streaming)"
          description="Chat with the agent using Server-Sent Events for streaming responses."
          requestBody={{
            message: "string (required)",
            headers: "object (optional)"
          }}
        />

        <Endpoint
          method="WS"
          path="/api/vanna/v2/chat_websocket"
          summary="Chat (WebSocket)"
          description="Real-time chat with the agent over WebSocket."
        />

        <Endpoint
          method="POST"
          path="/api/vanna/v2/chat_poll"
          summary="Chat (polling)"
          description="Chat with the agent using request/response polling."
        />

        <Endpoint
          method="GET"
          path="/health"
          summary="Root health check"
          description="Returns service health and available endpoints."
        />

        <Endpoint
          method="GET"
          path="/api/v1/conversation/history"
          summary="Get conversation history"
          description="Fetch recent conversation turns for a user/conversation."
          query={{
            user_identifier: "string (optional)",
            conversation_id: "string (optional)",
            limit: "integer (optional, default 10)"
          }}
        />

        <Endpoint
          method="GET"
          path="/api/v1/conversation/filter"
          summary="Filter conversations"
          description="Filter conversation history by keyword and/or user."
          query={{
            user_identifier: "string (optional)",
            conversation_id: "string (optional)",
            keyword: "string (optional)",
            limit: "integer (optional, default 10)"
          }}
        />

        <Endpoint
          method="DELETE"
          path="/api/v1/conversation/clear"
          summary="Clear conversation history"
          description="Clear conversation history for a user/conversation."
          query={{
            user_identifier: "string (optional)",
            conversation_id: "string (optional)"
          }}
        />

        <Endpoint
          method="GET"
          path="/api/v1/database/tables"
          summary="List database tables"
          description="Returns a list of tables in the connected database."
        />

        <Endpoint
          method="GET"
          path="/api/v1/memory/all"
          summary="Get agent memory"
          description="Returns recent agent memory entries (ChromaDB)."
          query={{
            limit: "integer (optional, default 100)"
          }}
        />

        <Endpoint
          method="GET"
          path="/api/v1/learning/detailed"
          summary="Detailed learning stats"
          description="Returns detailed learning statistics and example patterns."
        />

        <Endpoint
          method="GET"
          path="/api/v1/learning/patterns"
          summary="Get learning patterns"
          description="Returns learning patterns, optionally filtered by type."
          query={{
            pattern_type: '"query" | "tool" (optional)',
            limit: "integer (optional, default 10)"
          }}
        />

        <Endpoint
          method="POST"
          path="/api/v1/learning/enhance_test"
          summary="Test learning enhancement"
          description="Test the learning enhancement on a sample question."
          requestBody={{
            question: "string (required)"
          }}
        />
      </section>

      <section>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "1rem" }}>Error Handling</h2>
        <p>
          All endpoints return standard HTTP status codes. On error, the response will include a <code>detail</code> field with an error message.
        </p>
        <pre style={{
          background: "var(--background)",
          border: "1px solid var(--foreground)",
          padding: "1rem",
          borderRadius: 6,
          fontSize: "1rem",
          marginTop: "1rem",
          opacity: 0.8
        }}>
{`{
  "detail": "Error message here"
}`}
        </pre>
      </section>
    </main>
  );
}

function Endpoint({ method, path, summary, description, requestBody, response, query }) {
  return (
    <div style={{
      border: "1px solid var(--foreground)",
      borderRadius: 8,
      marginBottom: "2rem",
      padding: "1.2rem 1.5rem",
      background: "var(--background)",
      opacity: 0.9
    }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
        <span style={{
          display: "inline-block",
          fontWeight: 700,
          color: "#fff",
          background: method === "GET" ? "#0070f3" :
                      method === "POST" ? "#10b981" :
                      method === "DELETE" ? "#ef4444" :
                      method === "WS" ? "#f59e42" : "#888",
          borderRadius: 4,
          fontSize: "0.95rem",
          padding: "0.2rem 0.7rem",
          marginRight: 10,
          letterSpacing: 1
        }}>{method}</span>
        <code style={{ fontSize: "1.1rem", color: "var(--foreground)" }}>{path}</code>
      </div>
      <div style={{ marginBottom: 4 }}>
        <strong>{summary}</strong>
      </div>
      <div style={{ color: "var(--foreground)", marginBottom: 8, opacity: 0.8 }}>{description}</div>
      {query && (
        <div style={{ marginBottom: 8 }}>
          <strong>Query Parameters:</strong>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {Object.entries(query).map(([k, v]) => (
              <li key={k}><code>{k}</code>: {v}</li>
            ))}
          </ul>
        </div>
      )}
      {requestBody && (
        <div style={{ marginBottom: 8 }}>
          <strong>Request Body:</strong>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {Object.entries(requestBody).map(([k, v]) => (
              <li key={k}><code>{k}</code>: {v}</li>
            ))}
          </ul>
        </div>
      )}
      {response && (
        <div>
          <strong>Response:</strong>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {Object.entries(response).map(([k, v]) => (
              <li key={k}><code>{k}</code>: {v}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}