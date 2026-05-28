# PlotMap.py
import os
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle

def render_map(layers, title, filename_base, ellipses=None, targets=None, show_scale_bar=True):
    """
    Dynamic Map Rendering Engine
    Plots polygons from layers dictionary, handles color coding based on Class (L1->red, L2->green),
    annotates polygon centroids with 'ID : Class', and vertex nodes with their labels.
    """
    fig, ax = plt.subplots(figsize=(24, 20))
    
    for layer_name, gdf in layers.items():
        # Differentiate history/measured layout from updated conflated results
        is_faint = any(kw in layer_name.lower() for kw in ["original", "base", "measured", "distorted"])
        line_style = "--" if is_faint else "-"
        alpha_val = 0.25 if is_faint else 0.6
        line_width = 1.2 if is_faint else 1.5
        
        for idx, row in gdf.iterrows():
            geom = row['geometry']
            if geom is None or geom.is_empty:
                continue
                
            p_class = row.get('Class', 'L2')
            p_id = row.get('id', idx)
            
            # Rule: Class L1 -> red, Class L2 -> green
            edge_color = 'red' if p_class == 'L1' else 'green'
            
            # Render boundaries
            x, y = geom.exterior.xy
            ax.plot(x, y, color=edge_color, linestyle=line_style, linewidth=line_width, alpha=alpha_val)
            
            # Annotate ID : Class at polygon center
            centroid = geom.centroid
            ax.text(centroid.x, centroid.y, f"{p_id}:{p_class}", 
                    color=edge_color, fontsize=9, weight='bold', ha='center', va='center', alpha=min(alpha_val + 0.2, 1.0))
            
            # Annotate individual Vertex Labels
            vertex_col = None
            for col in ['Vertex_Sequenc', 'Vetex_Sequenc', 'Vertex_Sequence']:
                if col in row:
                    vertex_col = col
                    break
                    
            if vertex_col and row[vertex_col]:
                labels = [lbl.strip() for lbl in str(row[vertex_col]).split(',')]
                coords = list(geom.exterior.coords)
                for lbl, coord in zip(labels[:-1], coords[:-1]):
                    ax.plot(coord[0], coord[1], 'ko', markersize=2, alpha=alpha_val, zorder=3)
                    ax.text(coord[0] + 0.15, coord[1] + 0.15, lbl, 
                            fontsize=8, color='black', alpha=alpha_val, zorder=4)

    # Render error ellipses and target point nodes if provided by Step 2
    if targets:
        for label, (tx, ty) in targets.items():
            ax.plot(tx, ty, "ro", markersize=3, zorder=5)
            ax.text(tx + 0.15, ty + 0.15, label, fontsize=8, color='black', weight='bold', zorder=6)

            if ellipses and label in ellipses:
                param = ellipses[label]
                if param is not None:
                    ell = Ellipse(
                        xy=(tx, ty), width=param["width"], height=param["height"], angle=param["angle"],
                        edgecolor="darkblue", facecolor="skyblue", alpha=0.3, lw=1.0, zorder=4
                    )
                    ax.add_patch(ell)

    ax.set_aspect("equal")
    
    # Inject standard metric scale bar
    if show_scale_bar:
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        extent_x = xmax - xmin
        extent_y = ymax - ymin

        ideal_length = extent_x * 0.15
        possible_lengths = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000]
        scale_len = min(possible_lengths, key=lambda x: abs(x - ideal_length))
        half_len = scale_len / 2

        sb_x = xmax - (extent_x * 0.05) - scale_len
        sb_y = ymin + (extent_y * 0.04)
        sb_height = extent_y * 0.012
        text_y = sb_y + (sb_height * 1.5)

        ax.add_patch(Rectangle((sb_x, sb_y), half_len, sb_height, edgecolor='black', facecolor='black', zorder=10))
        ax.add_patch(Rectangle((sb_x + half_len, sb_y), half_len, sb_height, edgecolor='black', facecolor='white', zorder=10))

        ax.text(sb_x, text_y, "0", ha='center', va='bottom', fontsize=9, color='black', weight='bold', zorder=10)
        ax.text(sb_x + half_len, text_y, f"{half_len:g}", ha='center', va='bottom', fontsize=9, color='black', weight='bold', zorder=10)
        ax.text(sb_x + scale_len, text_y, f"{scale_len:g} m", ha='center', va='bottom', fontsize=9, color='black', weight='bold', zorder=10)

    plt.title(title, fontsize=11, weight="bold")
    plt.grid(True, linestyle=":", alpha=0.5)
    plt.xlabel("Easting / X Coordinate (meters)")
    plt.ylabel("Northing / Y Coordinate (meters)")

    dirname = os.path.dirname(filename_base)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
        
    plt.savefig(filename_base + ".png", dpi=300, bbox_inches='tight')
    plt.savefig(filename_base + ".svg", format='svg', bbox_inches='tight')
    plt.close()
    print(f"-> Map graphics successfully exported to {filename_base}.png and .svg")
