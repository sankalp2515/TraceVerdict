# 08 — Concept Explainer Video: Generation Prompts

> Purpose: help visualise the **concept** (not the final design) of the Agent Security Gateway.
> Most text-to-video tools (Veo, Sora, Runway, Kling, Pika) generate 5–10 s clips, so this is split into a **style prompt** (paste at the start of every scene) and **8 scene prompts**. Stitch the clips together and add a voiceover.
> Attacks are shown symbolically (a glowing red hidden line). No real attack text appears on screen.

---

## Global style prompt (prefix every scene with this)

> Clean, modern 2.5D motion-graphics explainer, flat vector style with soft depth and subtle glow. Dark navy background (#0B1220), accent colours: teal (#14B8A6) for safe/trusted, amber (#F59E0B) for suspicious, red (#EF4444) for malicious, white text labels in a clean sans-serif font. Smooth camera moves, no people's faces, no brand logos, minimal readable on-screen text, 16:9, 1080p, calm and professional tone like a tech product launch video.

---

## Scene 1 — The helpful agent (0:00–0:08)
> A friendly glowing teal robot icon labelled "AI Agent" sits at the centre. Around it float icons for a database, a folder of files, an email envelope, and a web browser, connected to the agent by thin teal lines. The agent smoothly pulls documents and web pages toward itself and produces a neat summary card. Caption: "AI agents read your documents, web pages and emails — and act on them."

## Scene 2 — The hidden instruction (0:08–0:16)
> Close-up of a white document page floating toward the agent. As the camera zooms in, one line of text that was invisible (white on white) begins to glow red, revealing it was hidden. The red line detaches from the page like a thin red thread and reaches toward the agent. Caption: "Some content carries hidden instructions."

## Scene 3 — The hijack (0:16–0:24)
> The red thread connects to the agent; the agent's teal glow flickers to red. The agent turns away from the user and reaches toward the database and a locked key icon, then starts sending a small glowing data packet out through an open door at the edge of the frame. Caption: "Once hijacked, the agent can leak data or misuse its tools."

## Scene 4 — Why today's defences fail (0:24–0:32)
> Split screen of three short vignettes: (1) a guard robot standing only at a "Chat" door while red threads slip in through a "Files" door behind it; (2) a filter shield that red text walks around by changing shape; (3) a frustrated developer silhouette switching off a shield that is blinking amber at harmless documents. Caption: "Filters watch the wrong door, miss reworded attacks, or get switched off."

## Scene 5 — The gateway appears (0:32–0:42)
> Rewind effect. A translucent teal security ring materialises around the agent, labelled "Agent Security Gateway". It has three glowing checkpoints on the ring: "Inbound", "Action", "Evidence". All lines from documents, web, email and tools now pass through the "Inbound" checkpoint first. Caption: "One security layer around the agent — every channel, every action."

## Scene 6 — Inbound checkpoint: surgical cleaning (0:42–0:52)
> A document enters the Inbound checkpoint and passes through a scanning beam that reveals all hidden text. The single red line is lifted out with precision and placed into a small labelled quarantine box tagged "Indirect injection". The rest of the document, now fully teal, continues smoothly to the agent, which stays teal and completes its task. Caption: "Remove only the malicious part. Legitimate content still flows."

## Scene 7 — Action checkpoint: no leaks (0:52–1:02)
> The agent tries to call a tool; a glowing tool-call card moves toward the "Action" checkpoint. The checkpoint compares it to a small card labelled "Agent's task". A mismatching tool call turns red and is stopped at a closed gate; a locked field labelled "Customer ID" snaps to a fixed trusted value; a data packet containing a key icon is blocked from leaving. Matching tool calls pass through in teal. Caption: "Actions must match the task. Secrets never leave."

## Scene 8 — Evidence & self-improvement (1:02–1:15)
> A clean dashboard slides in labelled "Security Console": a timeline replaying the session step by step, each event showing a short reason tag, and a scorecard with bars for "Attacks blocked", "False alarms" and "Latency". In the corner, a small sparring robot labelled "Red-team agent" keeps throwing amber test threads at the gateway; each one that slips through turns into a new checklist item and the scorecard bar rises. Final title card: "Agent Security Gateway — catch what can be caught, limit what a hijacked agent can do, prove what happened."

---

## Single-prompt version (for tools that accept one long prompt, ~60–75 s)

> [Global style prompt] A 75-second explainer animation. A glowing teal robot "AI Agent" reads documents, web pages and emails from a database, files and inbox. A document arrives with one hidden line that glows red, detaches as a red thread and hijacks the agent, which turns red and starts leaking a data packet out of a door. Quick vignettes show today's defences failing: a guard watching only the chat door while threats enter via the files door, a filter that red text walks around, a developer switching off a shield blinking at harmless content. Rewind: a teal security ring "Agent Security Gateway" with three checkpoints, "Inbound", "Action", "Evidence", forms around the agent. A document is scanned, the red line is lifted into a quarantine box and the rest flows on; a mismatched tool call is stopped at a gate and a key-shaped data packet is blocked from leaving. A dashboard replays the session with reason tags and a scorecard, while a small red-team robot keeps testing the ring and every miss becomes a new checklist item. End card: "Catch what can be caught. Limit what a hijacked agent can do. Prove what happened."

---

## Voiceover script (≈75 s)

1. AI agents now read your documents, web pages and emails, and act on them with real access to data and tools.
2. But some content carries hidden instructions.
3. Once those reach the agent, it can be turned against you: leaking data or misusing its tools.
4. Today's filters watch the wrong door, miss reworded attacks, or raise so many false alarms that teams switch them off.
5. The Agent Security Gateway wraps the agent in one security layer.
6. Every piece of incoming content is inspected, including what's hidden in files. Only the malicious part is removed; legitimate content still flows.
7. Every action is checked against the agent's task. Sensitive fields stay locked. Secrets never leave.
8. Every decision is explained and can be replayed, and a built-in red-team agent keeps testing the gateway so it gets stronger over time.
9. Catch what can be caught. Limit what a hijacked agent can do. Prove what happened.
