# 2_VtxCluster.py
import argparse
import numpy as np
import geopandas as gpd
from sklearn.cluster import DBSCAN
from shapely.geometry import Polygon
from scipy.optimize import least_squares
from pathlib import Path
import PlotMap  # Dynamic Map Rendering Engine


class ParcelVertexClustering:
    """Extracts vertices from discrete features, groups them via spatial clustering,
    and enforces target coordinates based on feature constraint classes.
    """
    def __init__(self, eps: float = 2.5, min_samples: int = 1):
        self.eps = eps
        self.min_samples = min_samples
        self.vertex_metadata = []
        self.X = None
        self.labels = None
        self.cluster_targets = {}

    def extract_and_cluster(self, gdf: gpd.GeoDataFrame) -> list:
        """Extracts polygon exterior coordinates, groups adjacent nodes via DBSCAN,
        and builds a target coordinate matrix.
        """
        vertices = []
        self.vertex_metadata = []

        has_Class_upper = "Class" in gdf.columns
        has_Class_lower = "class" in gdf.columns

        for idx, row in gdf.iterrows():
            pid = int(row["id"])

            if has_Class_upper:
                pcls = row["Class"]
            elif has_Class_lower:
                pcls = row["class"]
            else:
                pcls = "L1" if (pid == 1 or pid == 20) else "L2"

            coords = list(row["geometry"].exterior.coords)[:-1]

            for v_idx, pt in enumerate(coords):
                vertices.append([pt[0], pt[1]])
                self.vertex_metadata.append(
                    {"parcel_id": pid, "Class": pcls, "vertex_idx": v_idx}
                )

        self.X = np.array(vertices)

        db = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(self.X)
        self.labels = db.labels_

        for i, label in enumerate(self.labels):
            self.vertex_metadata[i]["cluster"] = int(label)

        self._compute_targets()
        return self.vertex_metadata

    def _compute_targets(self):
        unique_clusters = np.unique(self.labels)
        for cluster in unique_clusters:
            cluster_indices = np.where(self.labels == cluster)[0]
            cluster_pts = self.X[cluster_indices]

            l1_indices = [
                idx
                for idx in cluster_indices
                if self.vertex_metadata[idx]["Class"] == "L1"
            ]

            if len(l1_indices) > 0:
                target_xy = self.X[l1_indices[0]]
            else:
                target_xy = np.mean(cluster_pts, axis=0)

            self.cluster_targets[cluster] = target_xy

        for i, meta in enumerate(self.vertex_metadata):
            meta["target_x"] = self.cluster_targets[meta["cluster"]][0]
            meta["target_y"] = self.cluster_targets[meta["cluster"]][1]
            meta["orig_x"] = self.X[i][0]
            meta["orig_y"] = self.X[i][1]


class RigidSimilarityOptimizer:
    """Manages multi-element parameters mapping and computes optimal similarity transformations
    (4-DOF Translation, Scaling, Rotation) to resolve structural layout gaps.
    """
    def __init__(self, gdf: gpd.GeoDataFrame, vertex_metadata: list):
        self.gdf = gdf
        self.vertex_metadata = vertex_metadata
        self.unique_pids = sorted(gdf["id"].unique())

        pid_to_class = {m["parcel_id"]: m["Class"] for m in vertex_metadata}
        self.l2_pids = [pid for pid in self.unique_pids if pid_to_class[pid] != "L1"]

    @staticmethod
    def transform(xy: np.ndarray, tx: float, ty: float, s: float, theta: float) -> np.ndarray:
        x, y = xy[:, 0], xy[:, 1]
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        x_new = tx + s * (x * cos_t - y * sin_t)
        y_new = ty + s * (x * sin_t + y * cos_t)
        return np.column_stack((x_new, y_new))

    def _objective_function(self, p: np.ndarray) -> np.ndarray:
        residuals = []
        param_map = {}
        idx = 0

        for pid in self.l2_pids:
            param_map[pid] = {
                "tx": p[idx],
                "ty": p[idx + 1],
                "s": p[idx + 2],
                "theta": p[idx + 3],
            }
            idx += 4

        for pid in self.unique_pids:
            p_meta = [m for m in self.vertex_metadata if m["parcel_id"] == pid]
            if not p_meta:
                continue

            orig_xy = np.array([[m["orig_x"], m["orig_y"]] for m in p_meta])
            target_xy = np.array([[m["target_x"], m["target_y"]] for m in p_meta])

            if p_meta[0]["Class"] == "L1":
                tx, ty, s, theta = 0.0, 0.0, 1.0, 0.0
            else:
                tx = param_map[pid]["tx"]
                ty = param_map[pid]["ty"]
                s = param_map[pid]["s"]
                theta = param_map[pid]["theta"]

            transformed = self.transform(orig_xy, tx, ty, s, theta)
            residuals.extend((transformed - target_xy).ravel())

        return np.array(residuals)

    def optimize(self) -> dict:
        initial_params = np.tile([0.0, 0.0, 1.0, 0.0], len(self.l2_pids))
        res_opt = least_squares(self._objective_function, initial_params, method="lm")

        optimized_params = {}
        idx = 0
        for pid in self.l2_pids:
            optimized_params[pid] = {
                "tx": res_opt.x[idx],
                "ty": res_opt.x[idx + 1],
                "s": res_opt.x[idx + 2],
                "theta": res_opt.x[idx + 3],
            }
            idx += 4
        return optimized_params


class ParcelConflatorPipeline:
    def __init__(self, eps: float = 2.5):
        self.clusterer = ParcelVertexClustering(eps=eps)

    def run(self, input_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        metadata = self.clusterer.extract_and_cluster(input_gdf)
        optimizer = RigidSimilarityOptimizer(input_gdf, metadata)
        opt_params = optimizer.optimize()

        conflated_geoms = []
        for idx, row in input_gdf.iterrows():
            pid = int(row["id"])
            pcls = metadata[idx * 4]["Class"]

            orig_coords = np.array(row["geometry"].exterior.coords)

            if pcls == "L1":
                tx, ty, s, theta = 0.0, 0.0, 1.0, 0.0
            else:
                params = opt_params[pid]
                tx, ty, s, theta = params["tx"], params["ty"], params["s"], params["theta"]

            transformed_coords = optimizer.transform(orig_coords, tx, ty, s, theta)
            conflated_geoms.append(Polygon(transformed_coords))

        output_gdf = input_gdf.copy()
        output_gdf["geometry"] = conflated_geoms

        if "Class" in output_gdf.columns:
            output_gdf["Class"] = [metadata[i * 4]["Class"] for i in range(len(output_gdf))]
        elif "class" in output_gdf.columns:
            output_gdf["class"] = [metadata[i * 4]["Class"] for i in range(len(output_gdf))]
        else:
            output_gdf["Class"] = [metadata[i * 4]["Class"] for i in range(len(output_gdf))]

        return output_gdf


def main():
    parser = argparse.ArgumentParser(
        description="Execute multi-element rigid-body optimization transformations driven by DBSCAN node clustering."
    )
    parser.add_argument(
        "-e", "--epsilon",
        type=float,
        default=2.5,
        help="The search radius tolerance value (meters) used by DBSCAN clustering to identify shared nodes. (Default: 2.5)"
    )
    args = parser.parse_args()

    result_dir = Path("RESULT")
    input_gpkg = result_dir / "parcel_conflation_sim.gpkg"
    output_gpkg = result_dir / "parcel_conflation_results.gpkg"

    if not input_gpkg.exists():
        raise FileNotFoundError(f"Unable to trace baseline database at: {input_gpkg.resolve()}")

    print(f"Reading layer 'measured' from: {input_gpkg.name}...")
    gdf_measured = gpd.read_file(str(input_gpkg), layer="measured")

    print(f"Initializing conflator with DBSCAN epsilon threshold: {args.epsilon} meters")
    conflator = ParcelConflatorPipeline(eps=args.epsilon)
    gdf_conflated = conflator.run(gdf_measured)

    # Export configuration using clean echo statements
    print(f"Writing optimized results layer 'conflated' to database path: {output_gpkg}...")
    gdf_conflated.to_file(str(output_gpkg), layer="conflated", driver="GPKG")
    print("Conflation execution complete successfully.")

    # Render Post-Optimization Map with Labels
    print("Generating optimization state maps...")
    PlotMap.render_map(
        layers={"Conflated Layout": gdf_conflated},
        title=f"Post-Optimization Similarity Conflated Boundaries (Eps={args.epsilon}m)",
        filename_base="02_conflation_optimized"
    )

if __name__ == "__main__":
    main()
