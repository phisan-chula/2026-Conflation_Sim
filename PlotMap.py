# PlotMap.py
import matplotlib.pyplot as plt
import geopandas as gpd
from pathlib import Path

def render_map(layers: dict, title: str, filename_base: str, output_dir: str = "RESULT"):
    """
    Renders spatial layers with conditional styling:
    - L1 Parcels: Red fill, 0.5 alpha
    - L2 Parcels: Grey fill, 0.5 alpha
    - Labels: "ID: CLASS" at centroids
    - Outputs: PNG and SVG formats
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    for layer_name, gdf in layers.items():
        if gdf is None or gdf.empty:
            continue
            
        geom_type = gdf.geometry.iloc[0].geom_type if len(gdf) > 0 else "Unknown"
        
        if "Polygon" in geom_type:
            # Detect Class column (handle case sensitivity)
            class_col = "Class" if "Class" in gdf.columns else ("class" if "class" in gdf.columns else None)
            
            # --- Conditional Styling Engine ---
            if class_col:
                # Define color mapping
                facecolor_map = {"L1": "red", "L2": "grey"}
                # Assign colors per row, defaulting to lightgrey if class is unknown
                facecolors = gdf[class_col].map(facecolor_map).fillna("lightgrey")
                
                # Plot the filled polygons with alpha 0.5
                gdf.plot(
                    ax=ax, 
                    facecolor=facecolors, 
                    edgecolor="black", 
                    linewidth=1.2, 
                    alpha=0.5, 
                    label=layer_name
                )
            else:
                # Fallback for GDFs without class info
                gdf.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=1.0, linestyle="--")
            
            # --- Text Annotation Overlay (ID: CLASS) ---
            for _, row in gdf.iterrows():
                pid = row.get("id", "??")
                pcls = row.get(class_col, "") if class_col else ""
                label_text = f"{pid}: {pcls}" if pcls else f"{pid}"
                
                # Center placement via centroid math
                centroid = row["geometry"].centroid
                
                ax.text(
                    centroid.x, centroid.y, 
                    label_text,
                    fontsize=9, 
                    fontweight='bold',
                    color='black',
                    ha='center', 
                    va='center',
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
                )
                
        elif "Point" in geom_type:
            # Styled clustering nodes
            if "node_type" in gdf.columns:
                node_style = {"L1-Locked": "crimson", "L2-Centroid": "darkorange"}
                node_colors = gdf["node_type"].map(node_style).fillna("black")
                gdf.plot(ax=ax, color=node_colors, markersize=60, edgecolor="white", zorder=5, label=layer_name)
            else:
                gdf.plot(ax=ax, color='purple', markersize=30, zorder=5)

    # Decoration and Branding
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel("Easting (m)", fontsize=10)
    ax.set_ylabel("Northing (m)", fontsize=10)
    ax.grid(True, linestyle=':', alpha=0.4)
    ax.axis('equal')
    
    # Dual-format high fidelity export
    png_file = out_path / f"{filename_base}.png"
    plt.savefig(png_file, dpi=300, bbox_inches='tight')
    
    svg_file = out_path / f"{filename_base}.svg"
    plt.savefig(svg_file, format='svg', bbox_inches='tight')
    
    plt.close(fig)
    print(f"   [PlotMap] Layout '{filename_base}' exported (L1=Red, L2=Grey)")
