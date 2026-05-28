# 1_SimuParcel.py
import argparse
import os
import shutil
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.affinity import rotate, translate
import PlotMap  # Dynamic Map Rendering Engine

def get_node_name(r, c, cols):
    idx = r * (cols + 1) + c
    name = ""
    while idx >= 0:
        name = chr(idx % 26 + 65) + name
        idx = (idx // 26) - 1
    return name

def parse_move_arg(move_strings):
    move_dict = {}
    if not move_strings:
        return move_dict
    for item in move_strings:
        try:
            id_part, coord_part = item.split(':')
            pid = int(id_part)
            x_val, y_val = map(float, coord_part.split(','))
            move_dict[pid] = (x_val, y_val)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid format: '{item}'. Use ID:x,y")
    return move_dict

def main():
    parser = argparse.ArgumentParser(description="Simulate spatial layouts and apply optional customized coordinate shifts.")
    parser.add_argument("-m", "--move", "-s", "--shift", dest="move", nargs="+", type=str)
    args = parser.parse_args()
    
    user_shifts = parse_move_arg(args.move)
    result_dir = Path('./RESULT')
    if result_dir.exists():
        shutil.rmtree(result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    width, height, cols, rows = 10.0, 20.0, 10, 2
    np.random.seed(42)

    ideal_parcels, measured_parcels = [], []
    ids, colors, classes, vertex_sequences = [], [], [], []
    current_id = 1

    for r in range(rows):
        for c in range(cols):
            x_min, x_max = c * width, (c + 1) * width
            y_min, y_max = r * height, (r + 1) * height
            
            bl_name = get_node_name(r, c, cols)
            br_name = get_node_name(r, c + 1, cols)
            tr_name = get_node_name(r + 1, c + 1, cols)
            tl_name = get_node_name(r + 1, c, cols)
            v_seq = f"{bl_name},{br_name},{tr_name},{tl_name},{bl_name}"
            vertex_sequences.append(v_seq)
            
            poly_ideal = Polygon([(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)])
            ideal_parcels.append(poly_ideal)
            
            if current_id in [1, 20]:
                color, parcel_class = 'red', 'L1'
                poly_measured = translate(poly_ideal, xoff=user_shifts[current_id][0], yoff=user_shifts[current_id][1]) if current_id in user_shifts else poly_ideal
            else:
                color, parcel_class = 'blue', 'L2'
                if current_id in user_shifts:
                    poly_measured = translate(poly_ideal, xoff=user_shifts[current_id][0], yoff=user_shifts[current_id][1])
                else:
                    rotated_poly = rotate(poly_ideal, np.random.uniform(-4.0, 4.0), origin='center')
                    poly_measured = translate(rotated_poly, xoff=np.random.uniform(-0.8, 0.8), yoff=np.random.uniform(-0.8, 0.8))
                
            measured_parcels.append(poly_measured)
            ids.append(current_id)
            colors.append(color)
            classes.append(parcel_class)
            current_id += 1

    gdf_ideal = gpd.GeoDataFrame({'id': ids, 'Class': classes, 'color': colors, 'geometry': ideal_parcels}, crs="EPSG:32647")
    gdf_measured = gpd.GeoDataFrame({'id': ids, 'Class': classes, 'color': colors, 'Vertex_Sequenc': vertex_sequences, 'geometry': measured_parcels}, crs="EPSG:32647")

    gpkg_path = result_dir / "01_parcel_conflation_sim.gpkg"
    gdf_ideal.to_file(str(gpkg_path), layer="ideal", driver="GPKG")
    gdf_measured.to_file(str(gpkg_path), layer="measured", driver="GPKG")

    print("Generating simulation state layout map files via PlotMap...")
    PlotMap.render_map(
        layers={"Measured Distorted": gdf_measured},
        title="Simulation Layer Workspace Input (Measured with Nodes)",
        filename_base=str(result_dir / "01_simulation_input")
    )

if __name__ == "__main__":
    main()
