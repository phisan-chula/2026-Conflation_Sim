# 1_SimuParcel.py
import argparse
import numpy as np
from shapely.geometry import Polygon
from shapely.affinity import rotate, translate
import geopandas as gpd
from pathlib import Path
import PlotMap  # Dynamic Map Rendering Engine

def parse_move_arg(move_strings):
    """
    Parses input strings formatted as 'ID:x,y' into a dictionary mapping.
    Example: ['5:12.5,-5.0', '1:2.0,3.0'] -> {5: (12.5, -5.0), 1: (2.0, 3.0)}
    """
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
            raise argparse.ArgumentTypeError(
                f"Invalid move format: '{item}'. Must follow the strict 'ID:x,y' structure (e.g., 5:12.5,-5.0)"
            )
    return move_dict

def main():
    parser = argparse.ArgumentParser(
        description="Simulate spatial layouts and apply optional customized coordinate shifts to distinct parcels."
    )
    parser.add_argument(
        "-m", "--move",
        nargs="+",
        help="Specify user-defined manual shifts for parcels using the format ID:x,y (e.g., -m 5:12.5,-5.0 20:-3,4.5)",
        type=str
    )
    args = parser.parse_args()
    
    # Process user manual shifts mapping
    user_shifts = parse_move_arg(args.move)
    if user_shifts:
        print(f"Loaded manual user shifts for parcel IDs: {list(user_shifts.keys())}")

    # Initialize RESULT directory path string safely
    result_dir = Path('RESULT')
    result_dir.mkdir(parents=True, exist_ok=True)

    # Grid Layout parameters
    width = 10.0
    height = 20.0
    cols = 10
    rows = 2
    np.random.seed(42)

    ideal_parcels = []
    measured_parcels = []
    ids = []
    colors = []
    classes = []

    current_id = 1

    for r in range(rows):
        for c in range(cols):
            x_min = c * width
            x_max = x_min + width
            y_min = r * height
            y_max = y_min + height
            
            poly_ideal = Polygon([(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)])
            ideal_parcels.append(poly_ideal)
            
            # --- Class and Default Shift Logic Determinations ---
            if current_id == 1 or current_id == 20:
                color = 'red'
                parcel_class = 'L1'  # Anchor Class
                
                # Check if the user wants to forcefully override the L1 anchor's location
                if current_id in user_shifts:
                    x_shift, y_shift = user_shifts[current_id]
                    poly_measured = translate(poly_ideal, xoff=x_shift, yoff=y_shift)
                else:
                    poly_measured = poly_ideal
            else:
                color = 'blue'
                parcel_class = 'L2'  # General Class
                
                # If a manual shift is specified for this L2 parcel, use it; otherwise, use random distortions
                if current_id in user_shifts:
                    x_shift, y_shift = user_shifts[current_id]
                    rotation_deg = 0.0  # Reset rotation when manually placing precisely
                    rotated_poly = poly_ideal
                else:
                    # Rigid-body distortion matrix
                    x_shift = np.random.uniform(-0.8, 0.8)
                    y_shift = np.random.uniform(-0.8, 0.8)
                    rotation_deg = np.random.uniform(-4.0, 4.0)
                    rotated_poly = rotate(poly_ideal, rotation_deg, origin='center')
                
                poly_measured = translate(rotated_poly, xoff=x_shift, yoff=y_shift)
                
            measured_parcels.append(poly_measured)
            ids.append(current_id)
            colors.append(color)
            classes.append(parcel_class)
            current_id += 1

    # Convert matrices to structured GeoDataFrames containing the 'Class' attribute field
    gdf_ideal = gpd.GeoDataFrame({'id': ids, 'Class': classes, 'color': colors, 'geometry': ideal_parcels}, crs="EPSG:32647")
    gdf_measured = gpd.GeoDataFrame({'id': ids, 'Class': classes, 'color': colors, 'geometry': measured_parcels}, crs="EPSG:32647")

    gpkg_path = result_dir / "parcel_conflation_sim.gpkg"

    # Save multi-layer GeoPackage layers with explicit echoing
    print(f"Writing layer 'ideal' to database path: {gpkg_path}...")
    gdf_ideal.to_file(str(gpkg_path), layer="ideal", driver="GPKG")

    print(f"Writing layer 'measured' to database path: {gpkg_path}...")
    gdf_measured.to_file(str(gpkg_path), layer="measured", driver="GPKG")

    # Render Initial Layout State Map with Labels
    print("Generating simulation state maps...")
    PlotMap.render_map(
        layers={"Ideal Base": gdf_ideal, "Measured Distorted": gdf_measured},
        title="Simulation Layer Workspace Input (Ideal vs Measured)",
        filename_base="01_simulation_input"
    )

if __name__ == "__main__":
    main()
