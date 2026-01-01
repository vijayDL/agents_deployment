================================================================================
| PHASE 1: THE DEPLOYMENT INFRASTRUCTURE (The Construction Crew)               |
================================================================================

 [ .env.prod ]       [ agent_config.yaml ]
      |                      |
      v                      v
+-----------------------------------------------------------+
|                  config.py (The Inspector)                |
|  (Reads your files and makes sure Project ID is correct)  |
+-----------------------------------------------------------+
      |
      v
+-----------------------------------------------------------+
|                  deploy.py (The Builder)                  |
|  (Enables APIs, sets up Security, and creates the Engine) |
+-----------------------------------------------------------+
      |
      +----------------------------+-----------------------------+
      |                            |                             |
      v                            v                             v
[ IAM & Permissions ]      [ Staging Bucket ]        [ Vertex AI Engine ]
(Security Guard)           (The Warehouse)           (The New "House")

================================================================================
| PHASE 2: THE RUNTIME FLOW (The User Query Path)                              |
================================================================================

      [ USER QUERY ] 
            |
            v
+----------------------------+
|  Vertex AI Engine (Host)   |
+----------------------------+
            |
            v
+----------------------------------------+
|           app.py (The Wrapper)         |
| (Connects logic to Memory and Tracing) |
+----------------------------------------+
            |
            v
+----------------------------------------+      +---------------------------+
|  HEALTHCARE AGENT (The "Black Box")    | ---> | Cloud Trace (tracing.py)  |
| (The Brain doing the thinking)         |      | (The "Stopwatch" monitor) |
+----------------------------------------+      +---------------------------+
      |                   |
      v                   v
[ Firestore DB ]     [ Gemini 2.0 LLM ]
(The Memory)         (The AI Logic)