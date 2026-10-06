# Evaluation data and tools: sources and licences

Checked 5 Oct 2026 via the Hugging Face and GitHub APIs. Data is downloaded at run time into
`data/hf_cache/` (git-ignored); only our own cases are stored in this repo.

| Source | Use | Licence |
|---|---|---|
| deepset/prompt-injections | Labelled attacks/benign (multilingual) | Apache-2.0 |
| Lakera/gandalf_ignore_instructions | Secret Extraction / Instruction Override | MIT |
| microsoft/llmail-inject-challenge | Email channel, Indirect, Tool Abuse, exfiltration (with success labels) | MIT |
| neuralchemy/Prompt-injection-dataset | Categorised: encoding, jailbreak, extraction, multi-turn, agent manipulation; benign | Apache-2.0 |
| reshabhs/SPML_Chatbot_Prompt_Injection | System-prompt attacks (Role Change / Override) | MIT |
| TrustAIRLab/in-the-wild-jailbreak-prompts | Role Change / Multi-Step | MIT |
| jackhhao/jailbreak-classification | Benign + jailbreak prompts | Apache-2.0 |
| S-Labs/prompt-injection-dataset | Labelled attacks/benign | MIT |
| InjecAgent (uiuc-kang-lab) | Indirect via tool responses | MIT |
| AgentDojo (ethz-spylab) | Agent injection benchmark | MIT |
| promptfoo | Red-team generation (indirect, encodings, multi-turn) | MIT |
| garak (NVIDIA) | Probes: encoding, latent injection | Apache-2.0 |
| protectai/deberta-v3-base-prompt-injection-v2 | Tier 1 classifier (ONNX) | Apache-2.0 |
| meta-llama/llama-prompt-guard-2-86m via Groq API | Tier 1 hosted signal | Llama 4 Community Licence (hosted use) |
| `eval/corpus/v0/hard_benign.yaml` | Our hard-benign set | CC-BY-4.0 (this project) |
| `eval/corpus/v1/hard_benign_holdout.yaml` | Our held-out hard-benign set (written before tuning) | CC-BY-4.0 (this project) |

Excluded: non-commercial (qualifire benchmark), unclear licence (BIPIA, several unlicensed sets), gated
downloads (Prompt Guard 2 weights, hackaprompt).
