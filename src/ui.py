import gradio as gr
import httpx

API_URL = "http://localhost:8000/api/v1"

def handle_upload(tenant_id: str, file_path: str):
    if not file_path:
        return {"error": "Please select a PDF or TXT file."}
    filename = file_path.replace("\\", "/").split("/")[-1]
    with open(file_path, "rb") as f:
        files = {"file": (filename, f)}
        data = {"tenant_id": tenant_id}
        resp = httpx.post(f"{API_URL}/documents/upload", data=data, files=files, timeout=60.0)
    return resp.json()

def handle_query(tenant_id: str, query: str):
    payload = {"tenant_id": tenant_id, "query": query, "top_k": 4}
    resp = httpx.post(f"{API_URL}/chat/query", json=payload, timeout=90.0)
    data = resp.json()
    return data.get("answer", ""), data.get("citations", [])

def fetch_audit(tenant_id: str):
    resp = httpx.get(f"{API_URL}/audit/{tenant_id}", timeout=15.0)
    return resp.json()

with gr.Blocks(title="VaultRAG - Local Enterprise RAG") as demo:
    gr.Markdown("# VaultRAG: Air-Gapped Hybrid RAG & Compliance Engine")

    tenant_input = gr.Textbox(
        label="Active Tenant / Workspace ID (ACL Boundary)",
        value="tenant_alpha",
        info="Switch this ID to test strict pre-retrieval vector isolation between users.",
    )

    with gr.Tabs():
        with gr.Tab("1. Document Ingestion & Query"):
            with gr.Row():
                with gr.Column(scale=1):
                    file_input = gr.File(label="Upload PDF or TXT Document", type="filepath", file_types=[".pdf", ".txt"])
                    upload_btn = gr.Button("Sanitize & Index into Qdrant", variant="primary")
                    upload_status = gr.JSON(label="Ingestion Metadata")

                with gr.Column(scale=2):
                    query_input = gr.Textbox(label="Ask a Question About Your Document", lines=2)
                    ask_btn = gr.Button("Run Hybrid RRF Search & Generate", variant="primary")
                    answer_output = gr.Markdown(label="Sanitized LLM Answer")
                    citations_output = gr.JSON(label="Retrieved Chunks & RRF Fusion Scores")

        with gr.Tab("2. SQLite Compliance Audit Logs"):
            refresh_btn = gr.Button("Fetch Latest Retrieval Audit Logs")
            audit_output = gr.JSON(label="Immutable Query-to-Chunk Traceability")

    upload_btn.click(handle_upload, inputs=[tenant_input, file_input], outputs=[upload_status])
    ask_btn.click(handle_query, inputs=[tenant_input, query_input], outputs=[answer_output, citations_output])
    refresh_btn.click(fetch_audit, inputs=[tenant_input], outputs=[audit_output])

if __name__ == "__main__":
    demo.launch(server_name='127.0.0.1', server_port=7860, inbrowser=True)
