# 3_TopoSnap.py
import argparse
import numpy as np
import geopandas as gpd
from sklearn.cluster import DBSCAN
from shapely.geometry import Polygon, Point
from pathlib import Path
import PlotMap  # Dynamic Map Rendering Engine


class VertexExtractor:
    @staticmethod
    def extract(gdf: gpd.GeoDataFrame) -> tuple:
        vertices = []
        metadata = []

        for idx, row in gdf.iterrows():
            pid = int(row["id"])
            pcls = row["Class"] if "Class" in gdf.columns else row.get("class", "L2")
            coords = list(row["geometry"].exterior.coords)

            for v_idx, pt in enumerate(coords):
                vertices.append([pt[0], pt[1]])
                metadata.append(
                    {
                        "parcel_id": pid,
                        "Class": pcls,
                        "vertex_idx": v_idx,
                        "is_closing": (v_idx == len(coords) - 1),
                    }
                )

        return np.array(vertices), metadata


class TopologicalClusterEngine:
    def __init__(self, eps: float = 1.5, min_samples: int = 1):
        self.eps = eps
        self.min_samples = min_samples

    def process_clusters(self, X: np.ndarray, metadata: list) -> dict:
        non_closing_idx = [i for i, m in enumerate(metadata) if not m["is_closing"]]
        X_fit = X[non_closing_idx]

        db = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(X_fit)
        labels_fit = db.labels_

        fit_cursor = 0
        parcel_v0_cluster = {}
        for i, m in enumerate(metadata):
            if not m["is_closing"]:
                m["cluster"] = int(labels_fit[fit_cursor])
                if m["vertex_idx"] == 0:
                    parcel_v0_cluster[m["parcel_id"]] = m["cluster"]
                fit_cursor += 1

        for m in metadata:
            if m["is_closing"]:
                m["cluster"] = parcel_v0_cluster[m["parcel_id"]]

        cluster_stats = {}
        unique_clusters = np.unique(labels_fit)

        for cluster in unique_clusters:
            c_indices = [
                i
                for i, m in enumerate(metadata)
                if m["cluster"] == cluster and not m["is_closing"]
            ]
            pts = X[c_indices]
            m_sub = [metadata[i] for i in c_indices]

            l1_indices = [i for i, m in enumerate(m_sub) if m["Class"] == "L1"]

            if len(l1_indices) > 0:
                target_xy = pts[l1_indices[0]]
                is_l1_locked = True
            else:
                target_xy = np.mean(pts, axis=0)
                is_l1_locked = False

            sq_errors = np.sum((pts - target_xy) ** 2, axis=1)
            rmse = np.sqrt(np.mean(sq_errors))

            cluster_stats[cluster] = {
                "target_x": target_xy[0],
                "target_y": target_xy[1],
                "rmse": rmse,
                "is_fixed_by_l1": is_l1_locked,
                "num_vertices": len(pts),
            }

        return cluster_stats


class TopologicalSnappingPipeline:
    def __init__(self, eps: float = 1.5):
        self.extractor = VertexExtractor()
        self.cluster_engine = TopologicalClusterEngine(eps=eps)

    def execute_snapping(self, gdf: gpd.GeoDataFrame) -> tuple:
        X, metadata = self.extractor.extract(gdf)
        cluster_stats = self.cluster_engine.process_clusters(X, metadata)

        for m, pt in zip(metadata, X):
            stat = cluster_stats[m["cluster"]]
            m["target_x"] = stat["target_x"]
            m["target_y"] = stat["target_y"]
            m["cluster_rmse"] = stat["rmse"]

        snapped_polygons = []
        unique_pids = sorted(gdf["id"].unique())

        for pid in unique_pids:
            p_meta = sorted(
                [m for m in metadata if m["parcel_id"] == pid],
                key=lambda x: x["vertex_idx"],
            )
            new_coordinates = [(m["target_x"], m["target_y"]) for m in p_meta]
            snapped_polygons.append(Polygon(new_coordinates))

        gdf_parcels_out = gdf.copy()
        gdf_parcels_out["geometry"] = snapped_polygons

        c_ids, c_pts, c_rmses, c_types, c_sizes = [], [], [], [], []
        for c_id, stat in cluster_stats.items():
            c_ids.append(c_id)
            c_pts.append(Point(stat["target_x"], stat["target_y"]))
            c_rmses.append(stat["rmse"])
            c_types.append("L1-Locked" if stat["is_fixed_by_l1"] else "L2-Centroid")
            c_sizes.append(stat["num_vertices"])

        gdf_nodes_out = gpd.GeoDataFrame(
            {
                "cluster_id": c_ids,
                "rmse": c_rmses,
                "node_type": c_types,
                "vertex_count": c_sizes,
            },
            geometry=c_pts,
            crs=gdf.crs,
        )

        return gdf_parcels_out, gdf_nodes_out


def main():
    parser = argparse.ArgumentParser(
        description="Execute final topological boundary snapping routines driven by adjustable DBSCAN parameters."
    )
    parser.add_argument(
        "-e", "--epsilon",
        type=float,
        default=1.5,
        help="The search radius tolerance value (meters) used by DBSCAN to force adjacent corner vertices to snap together. (Default: 1.5)"
    )
    args = parser.parse_args()

    result_dir = Path("RESULT")
    input_path = result_dir / "parcel_conflation_results.gpkg"
    output_path = result_dir / "parcel_conflation_topo_snapped.gpkg"

    if not input_path.exists():
        raise FileNotFoundError(f"Unable to find post-optimization layer at: {input_path.resolve()}")

    print(f"Reading layer 'conflated' from: {input_path.name}...")
    gdf_conflated = gpd.read_file(str(input_path), layer="conflated")

    print(f"Initializing snapping engine with DBSCAN epsilon threshold: {args.epsilon} meters")
    pipeline = TopologicalSnappingPipeline(eps=args.epsilon)
    gdf_snapped_parcels, gdf_cluster_nodes = pipeline.execute_snapping(gdf_conflated)

    # Export structural data frames to tables with clear print indicators
    print(f"Writing boundary layer 'snapped_parcels' to database path: {output_path}...")
    gdf_snapped_parcels.to_file(str(output_path), layer="snapped_parcels", driver="GPKG")

    print(f"Writing analytical node points layer 'cluster_nodes' to database path: {output_path}...")
    gdf_cluster_nodes.to_file(str(output_path), layer="cluster_nodes", driver="GPKG")
    print("Database processing execution complete.")

    # Render Final Topological Network State Map with Labels
    print("Generating final topological snapped maps...")
    PlotMap.render_map(
        layers={"Snapped Boundaries": gdf_snapped_parcels, "Cluster Nodes": gdf_cluster_nodes},
        title=f"Final Topological Snapping Network (Eps={args.epsilon}m)",
        filename_base="03_topological_snapped"
    )

if __name__ == "__main__":
    main()
