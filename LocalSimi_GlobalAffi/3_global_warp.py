# 03_pw_transf.py
import os
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import PlotMap  # Centralized Dynamic Map Rendering Engine

class PiecewiseControlWarpPipeline:
    def __init__(self, result_dir="RESULT", input_filename="02_parcel_conflation_aligned.gpkg"):
        self.result_dir = result_dir
        self.input_gpkg = os.path.join(result_dir, input_filename)
        
        # New structured output file configuration for the warping phase
        self.output_gpkg = os.path.join(result_dir, "03_global_aligned.gpkg")
        self.output_layer_name = "global_aligned"
        
        # Schema layer configuration
        self.layer_name = "aligned_parcels"
        self.vertex_col = "Vertex_Sequenc"
        
        self.gdf_all = None
        self.gdf_l1 = None
        self.gdf_l2 = None
        self.gdf_l2_transformed = None
        self.affine_matrix = None
        self.control_targets = {}  # Dynamically harvested from L1 anchor features

    def run_transform_pipeline(self):
        """Executes the control point pairing, affine model estimation, and global fabric warp."""
        self._load_prior_alignment_data()
        src_pts, dst_pts = self._pair_control_nodes_dynamically()
        self._estimate_global_affine_warp(src_pts, dst_pts)
        self._warp_l2_parcel_fabric()
        self._generate_and_save_plots()
        self._export_to_structured_geopackage()

    def _load_prior_alignment_data(self):
        """Loads the multi-class parcel layer generated in the prior step."""
        if not os.path.exists(self.input_gpkg):
            raise FileNotFoundError(f"[ERROR] Cannot find the prior step file at: {self.input_gpkg}")
            
        print(f"Reading layer '{self.layer_name}' from prior step database: {self.input_gpkg}...")
        self.gdf_all = gpd.read_file(self.input_gpkg, layer=self.layer_name)
        
        # Separate the anchor structures (L1) and adjustable parcellation grid (L2)
        self.gdf_l1 = self.gdf_all[self.gdf_all["Class"] == "L1"].copy()
        self.gdf_l2 = self.gdf_all[self.gdf_all["Class"] == "L2"].copy()

    def _pair_control_nodes_dynamically(self):
        """
        Extracts control coordinates from L1 features and finds matching 
        shared boundary node points inside the L2 polygons to build tie-pairs.
        """
        print("Extracting absolute anchor point coordinates from Class L1 reference polygons...")
        for idx, row in self.gdf_l1.iterrows():
            val = str(row[self.vertex_col]).strip() if row[self.vertex_col] is not None else ""
            if not val or val.lower() == 'nan': 
                continue
            labels = [lbl.strip() for lbl in val.split(",")]
            coords = list(row["geometry"].exterior.coords)
            
            # Map unique reference vertices (ignoring the redundant closing vertex loop)
            for label, coord in zip(labels[:-1], coords[:-1]):
                self.control_targets[label] = coord
        
        print(f"-> Active L1 anchor control markers identified: {sorted(list(self.control_targets.keys()))}")

        print("Locating topological matching points inside Class L2 polygons...")
        src_pts = []
        dst_pts = []
        
        for idx, row in self.gdf_l2.iterrows():
            val = str(row[self.vertex_col]).strip() if row[self.vertex_col] is not None else ""
            if not val or val.lower() == 'nan': 
                continue
            labels = [lbl.strip() for lbl in val.split(",")]
            coords = list(row["geometry"].exterior.coords)
            
            for label, coord in zip(labels[:-1], coords[:-1]):
                # If an L2 vertex label matches an L1 control node, register it as a tie-point
                if label in self.control_targets:
                    src_pts.append(coord)
                    dst_pts.append(self.control_targets[label])
                    
        print(f"-> Successfully paired {len(src_pts)} control node tie-points for warp model fitting.")
        return np.array(src_pts), np.array(dst_pts)

    def _estimate_global_affine_warp(self, src_pts, dst_pts):
        """Computes a global 6-parameter Affine matrix using Least-Squares regression."""
        print("Fitting global Affine Warp Model via Least-Squares regression...")
        
        # Pad source coordinate pairs with a column of ones for affine transformation tensor math
        X = np.hstack([src_pts, np.ones((len(src_pts), 1))])
        Y = dst_pts
        
        # Solve the linear system: X * M = Y
        M, residuals, rank, s = np.linalg.lstsq(X, Y, rcond=None)
        self.affine_matrix = M
        print("-> Global Affine transformation matrix successfully computed.")

    def _warp_geometry(self, poly):
        """Applies the computed global affine matrix transformation matrix to a polygon structure."""
        coords = np.array(poly.exterior.coords)
        padded_coords = np.hstack([coords, np.ones((len(coords), 1))])
        warped_coords = np.dot(padded_coords, self.affine_matrix)
        return Polygon(warped_coords)

    def _warp_l2_parcel_fabric(self):
        """Warps all adjustable Class L2 geometries using the global transformation matrix."""
        print("Warping all Class L2 features to match the L1 anchor boundaries...")
        warped_geometries = []
        for idx, row in self.gdf_l2.iterrows():
            warped_geometries.append(self._warp_geometry(row["geometry"]))
            
        self.gdf_l2_transformed = self.gdf_l2.copy()
        self.gdf_l2_transformed["geometry"] = warped_geometries

    def _generate_and_save_plots(self):
        """Delegates layout visualization directly to your centralized PlotMap module."""
        print("Rendering map sheets... Delegating visual layouts to PlotMap module...")
        layers = {
            "Class L1 Anchor Framework": self.gdf_l1,
            "Prior Step Aligned Base": self.gdf_l2,
            "Warped Conflation Output": self.gdf_l2_transformed
        }
        
        # Generates high-density raster .png and crisp vector .svg files using unified specs
        PlotMap.render_map(
            layers=layers,
            title="Global Affine Fabric Warp: Layer Conflation via Shared L1 Control Mesh",
            filename_base=os.path.join(self.result_dir, "03_conflation_result"),
            targets=self.control_targets
        )

    def _export_to_structured_geopackage(self):
        """Compiles unmodified L1 anchors and newly warped L2 features into the final structured file."""
        print("Compiling fixed anchors and transformed L2 features into structured schema layout...")
        output_gdf = gpd.pd.concat([self.gdf_l1, self.gdf_l2_transformed], ignore_index=True)
        output_gdf = gpd.GeoDataFrame(output_gdf, geometry='geometry', crs=self.gdf_all.crs)
        
        if os.path.exists(self.output_gpkg):
            os.remove(self.output_gpkg)
            
        print(f"Writing all attributes and 'Vertex_Sequenc' mapping fields to structured file: {self.output_gpkg}...")
        output_gdf.to_file(self.output_gpkg, layer=self.output_layer_name, driver="GPKG")
        print(f"-> Structured GeoPackage layer '{self.output_layer_name}' successfully written.")

if __name__ == "__main__":
    pipeline = PiecewiseControlWarpPipeline()
    pipeline.run_transform_pipeline()
