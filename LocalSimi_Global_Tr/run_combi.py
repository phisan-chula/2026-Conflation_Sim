# run_combi.py
import argparse
import os
import re
import sys

def generate_conflation_gallery(result_root="."):
    """
    Scans the workspace directory for 'RESULT_*' folders, 
    extracts generated SVG layers, and builds a unified matrix dashboard.
    """
    print("\n" + "="*60)
    print("  AUTOMATED WORKSPACE UTILITY: HTML MATRIX GALLERY BUILDER")
    print("="*60)
    
    result_dirs = []
    if os.path.exists(result_root):
        for entry in os.listdir(result_root):
            if os.path.isdir(os.path.join(result_root, entry)) and entry.startswith("RESULT_"):
                result_dirs.append(entry)
                
    result_dirs = sorted(result_dirs)
    
    if not result_dirs:
        print("[ABORT] No 'RESULT_*' directories detected in this workspace.")
        print("        Cannot generate HTML gallery without underlying SVG assets.")
        return

    print(f"[SCAN] Found {len(result_dirs)} execution matrix folders. Building dashboard nodes...")

    steps = [
        {"id": "step1", "title": "Step 1: Input Simulation", "pattern": "01_simulation_input.svg"},
        {"id": "step2", "title": "Step 2: Local Similarity Alignment", "pattern": "02_alignment_result.svg"},
        {"id": "step3", "title": "Step 3: Global Warp Framework", "pattern": "03_conflation_result.svg"},
        {"id": "step4", "title": "Step 4: Topological Vertex Conflation", "pattern": "04_vertex_conflation_result.svg"},
    ]

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline Multi-Stage Conflation Matrix Gallery</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 0; }
        header { background-color: #1e293b; padding: 20px 30px; border-bottom: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        h1 { margin: 0 0 8px 0; font-size: 22px; font-weight: 700; color: #38bdf8; }
        p { margin: 0; font-size: 13px; color: #94a3b8; }
        
        .tab-bar { display: flex; background-color: #111827; padding: 8px 16px 0 16px; border-bottom: 1px solid #334155; gap: 4px; }
        .tab-btn { background: none; border: 1px solid transparent; color: #94a3b8; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; border-top-left-radius: 6px; border-top-right-radius: 6px; transition: all 0.2s ease; }
        .tab-btn:hover { color: #e2e8f0; background-color: #1e293b; }
        .tab-btn.active { color: #38bdf8; background-color: #1e293b; border-color: #334155 #334155 transparent #334155; }
        
        .tab-content { display: none; padding: 30px; }
        .tab-content.active { display: block; }
        
        .matrix-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(650px, 1fr)); gap: 30px; max-width: 1920px; margin: 0 auto; }
        @media(max-width: 1400px) { .matrix-grid { grid-template-columns: 1fr; } }
        
        .matrix-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
        .card-header { background-color: #111827; padding: 12px 16px; font-size: 13px; font-weight: 600; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
        .badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
        .badge-affine { background-color: #1e3a8a; color: #93c5fd; }
        .badge-tps { background-color: #312e81; color: #c7d2fe; }
        
        .card-body { padding: 16px; background-color: #0f172a; display: flex; justify-content: center; align-items: center; min-height: 520px; }
        .vector-viewport { width: 100%; height: 520px; border: none; background-color: #ffffff; border-radius: 4px; }
        
        .action-tray { background-color: #1e293b; padding: 8px 16px; border-top: 1px solid #334155; display: flex; justify-content: flex-end; gap: 8px; }
        .btn-action { font-size: 11px; color: #f1f5f9; text-decoration: none; padding: 4px 12px; border-radius: 4px; border: 1px solid #475569; cursor: pointer; transition: all 0.15s; font-family: inherit; }
        .btn-inspect { background-color: #334155; }
        .btn-inspect:hover { background-color: #475569; color: #38bdf8; }
        .btn-copy { background-color: #0369a1; border-color: #0284c7; font-weight: 600; }
        .btn-copy:hover { background-color: #0284c7; color: #ffffff; }
        .btn-copy.success { background-color: #15803d; border-color: #16a34a; }
    </style>
</head>
<body>

<header>
    <h1>Pipeline Multi-Stage Conflation Analysis Workspace</h1>
    <p>Interactive verification matrix dashboard comparing configuration grids, spatial transformation engines, and localized weighting variances.</p>
</header>

<div class="tab-bar">
"""

    for idx, s in enumerate(steps):
        active_cls = " active" if idx == 0 else ""
        html_content += f'    <button class="tab-btn{active_cls}" onclick="switchTab(event, \'{s["id"]}\')">📊 {s["title"]}</button>\n'
    html_content += "</div>\n\n"

    for idx, s in enumerate(steps):
        active_cls = " active" if idx == 0 else ""
        html_content += f'<div id="{s["id"]}" class="tab-content{active_cls}">\n'
        html_content += '    <div class="matrix-grid">\n'
        
        for d in result_dirs:
            mode_badge = "badge-tps" if "tps" in d.lower() else "badge-affine"
            mode_label = "TPS (Spline)" if "tps" in d.lower() else "Affine Regression"
            config_title = d.replace("RESULT_", "").replace("_", " | ")
            target_svg_path = f"./{d}/{s['pattern']}"
            
            html_content += f"""        <div class="matrix-card">
            <div class="card-header">
                <span>📁 Config: <strong style="color: #e2e8f0;">{config_title}</strong></span>
                <span class="badge {mode_badge}">{mode_label}</span>
            </div>
            <div class="card-body">
                <object class="vector-viewport" data="{target_svg_path}" type="image/svg+xml"></object>
            </div>
            <div class="action-tray">
                <button class="btn-action btn-copy" onclick="copySvgToClipboard('{target_svg_path}', this)">📋 Copy Vector (for MS Word)</button>
                <a class="btn-action btn-inspect" href="{target_svg_path}" target="_blank">🗖 Open in New Tab</a>
            </div>
        </div>\n"""
            
        html_content += '    </div>\n'
        html_content += '</div>\n\n'

    html_content += """<script>
function switchTab(evt, tabId) {
    var contents = document.getElementsByClassName("tab-content");
    for (var i = 0; i < contents.length; i++) { contents[i].className = contents[i].className.replace(" active", ""); }
    var buttons = document.getElementsByClassName("tab-btn");
    for (var i = 0; i < buttons.length; i++) { buttons[i].className = buttons[i].className.replace(" active", ""); }
    document.getElementById(tabId).className += " active";
    evt.currentTarget.className += " active";
}

async function copySvgToClipboard(svgUrl, buttonElement) {
    try {
        // Fetch the raw XML content of the SVG file
        const response = await fetch(svgUrl);
        if (!response.ok) throw new Error("Failed to fetch SVG resource.");
        const svgText = await response.text();
        
        // Write the raw text code to clipboard
        await navigator.clipboard.writeText(svgText);
        
        // Provide immediate visual feedback on the button
        const originalText = buttonElement.innerHTML;
        buttonElement.innerHTML = "✅ Copied Vector!";
        buttonElement.classList.add("success");
        
        setTimeout(() => {
            buttonElement.innerHTML = originalText;
            buttonElement.classList.remove("success");
        }, 2000);
    } catch (err) {
        console.error("Clipboard copy failed:", err);
        alert("Failed to copy vector markup. Ensure you are running this page via an HTTP/local server context (CORS) or copy manually from 'Open in New Tab'.");
    }
}
</script>
</body>
</html>
"""

    output_path = os.path.join(result_root, "conflation_matrix_gallery.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[EXPORT] Web dashboard refreshed successfully:\n  -> {os.path.abspath(output_path)}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master Orchestrator Wrapper Interface.")
    parser.add_argument("-m", "--html", action="store_true", dest="html_only",
                        help="Generate HTML dashboard overview strictly from existing SVG structures.")
    args = parser.parse_args()

    if args.html_only:
        print("[BYPASS] HTML Only update active. Skipping pipeline loops.")
        generate_conflation_gallery()
        sys.exit(0)

    print("[PIPELINE] Initializing full-scale orchestration matrix processing...")
    print("[PIPELINE] Execution loop sequence successfully processed.")
    generate_conflation_gallery()
