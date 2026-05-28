# 2_Align_Transf.py
import os
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import PlotMap  # Dynamic Map Rendering Engine

class ParcelConflationPipeline:
    def __init__(self, result_dir="RESULT", input_filename="01_parcel_conflation_sim.gpkg"):
        self.result_dir = result_dir
        self.input_gpkg = os.path.join(result_dir, input_filename)
        self.output_gpkg = os.path.join(result_dir, "02_parcel_conflation_aligned.gpkg")
        self.output_layer_name = "aligned_parcels"
        self.layer_name = "measured"
        self.vertex_col = "Vertex_Sequenc"
        
        self.gdf_all = None
        self.gdf_filtered = None
        self.gdf_l1 = None
        self.gdf_transformed = None
        self.targets = {}
        self.ellipses = {}

    def run_pipeline(self):
        self._load_and_filter_data()
        self._calculate_targets_and_ellipses()
        self._align_parcels_rigidly()
        self._generate_and_save_plots()
        self._export_results_to_new_geopackage()

    def _load_and_filter_data(self):
        self.gdf_all = gpd.read_file(self.input_gpkg, layer=self.layer_name)
        self.gdf_filtered = self.gdf_all[self.gdf_all["Class"] != "L1"].copy()
        self.gdf_l1 = self.gdf_all[self.gdf_all["Class"] == "L1"].copy()

    def _calculate_targets_and_ellipses(self):
        vertex_groups = {}
        for idx, row in self.gdf_filtered.iterrows():
            val = str(row[self.vertex_col]).strip() if row[self.vertex_col] is not None else ""
            if not val or val.lower() == 'nan': continue
            labels = [lbl.strip() for lbl in val.split(",")]
            coords = list(row["geometry"].exterior.coords)
            for label, coord in zip(labels, coords):
                if label not in vertex_groups: vertex_groups[label] = []
                vertex_groups[label].append(coord)

        for label, pts in vertex_groups.items():
            pts = np.array(pts)
            mean_x, mean_y = np.mean(pts, axis=0)
            self.targets[label] = (mean_x, mean_y)
            if len(pts) >= 3:
                cov = np.cov(pts.T)
                eigenvalues, eigenvectors = np.linalg.eigh(cov)
                order = eigenvalues.argsort()[::-1]
                eigenvalues, eigenvectors = eigenvalues[order], eigenvectors[:, order]
                angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
                chi_scale = 2.447
                self.ellipses[label] = {
                    "width": chi_scale * np.sqrt(max(0, eigenvalues[0])) * 2,
                    "height": chi_scale * np.sqrt(max(0, eigenvalues[1])) * 2,
                    "angle": angle
                }
            else:
                self.ellipses[label] = None

    @staticmethod
    def _estimate_similarity_transform(src_pts, dst_pts):
        src_centroid, dst_centroid = np.mean(src_pts, axis=0), np.mean(dst_pts, axis=0)
        src_centered, dst_centered = src_pts - src_centroid, dst_pts - dst_centroid
        H = np.dot(src_centered.T, dst_centered)
        U, S, Vt = np.linalg.svd(H)
        R = np.dot(Vt.T, U.T)
        if np.linalg.det(R) < 0:
            Vt[1, :] *= -1
            R = np.dot(Vt.T, U.T)
        scale = np.sum(S) / np.sum(src_centered**2)
        translation = dst_centroid - scale * np.dot(R, src_centroid)
        return scale, R, translation

    def _transform_polygon(self, poly, labels):
        src_pts = np.array(poly.exterior.coords)[:-1]
        val = str(labels).strip() if labels is not None else ""
        poly_labels = [lbl.strip() for lbl in val.split(",")][:-1]
        dst_pts = np.array([self.targets[lbl] for lbl in poly_labels if lbl in self.targets])
        if len(dst_pts) < 2: return poly
        scale, R, t = self._estimate_similarity_transform(src_pts[: len(dst_pts)], dst_pts)
        all_coords = np.array(poly.exterior.coords)
        transformed_coords = scale * np.dot(all_coords, R.T) + t
        return Polygon(transformed_coords)

    def _align_parcels_rigidly(self):
        transformed_geometries = []
        for idx, row in self.gdf_filtered.iterrows():
            new_poly = self._transform_polygon(row["geometry"], row[self.vertex_col])
            transformed_geometries.append(new_poly)
        self.gdf_transformed = self.gdf_filtered.copy()
        self.gdf_transformed["geometry"] = transformed_geometries

    def _generate_and_save_plots(self):
        """Delegates all visualization work directly to the centralized PlotMap module."""
        print("Delegating visual plotting execution to PlotMap module...")
        layers = {}
        if not self.gdf_l1.empty:
            layers["Class L1 (Reference)"] = self.gdf_l1
        layers["Original Base Layer"] = self.gdf_filtered
        layers["Conflated Layout Output"] = self.gdf_transformed
        
        PlotMap.render_map(
            layers=layers,
            title="Parcel Alignment & True-Scale 95% Confidence Error Ellipses",
            filename_base=os.path.join(self.result_dir, "02_conflation_result"),
            ellipses=self.ellipses,
            targets=self.targets
        )

    def _export_results_to_new_geopackage(self):
        output_gdf = gpd.pd.concat([self.gdf_l1, self.gdf_transformed], ignore_index=True)
        output_gdf = gpd.GeoDataFrame(output_gdf, geometry='geometry', crs=self.gdf_all.crs)
        if os.path.exists(self.output_gpkg):
            os.remove(self.output_gpkg)
        output_gdf.to_file(self.output_gpkg, layer=self.output_layer_name, driver="GPKG")
        print(f"-> Successfully generated new layer at: {self.output_gpkg}")

if __name__ == "__main__":
    pipeline = ParcelConflationPipeline()
    pipeline.run_pipeline()
