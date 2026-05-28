# 2026-Parcel Conflation

# Geometric Warping Approaches: Global Similarity vs. Hybrid Local Similarity & Global Affine

When rectifying historical land surveys, adjusting cadastral parcel layers, or matching legacy maps to a modern geodetic baseline, managing geometric distortions requires a deliberate trade-off between **global consistency** and **local accuracy**.

This document outlines the mathematical frameworks and operational differences between **Global Similarity Transformations** and a hybrid **Local Similarity + Global Affine Transformation** pipeline.

---

## 1. Global Similarity Transformation

A global similarity transformation applies a single, uniform geometric adjustment across the entire spatial dataset. It preserves the exact shape of the geometries while minimizing the overall global root-mean-square error (RMSE) using a least-squares optimization across all control points.

### Mathematical Framework
The transformation modifies coordinates using exactly **four parameters**: translation ($\Delta x, \Delta y$), rotation angle ($\theta$), and a uniform scale factor ($s$). 

The forward transformation for a source point $(x, y)$ to a target point $(x', y')$ is expressed as:

$$
\begin{bmatrix} 
x' \\ 
y' 
\end{bmatrix} = 
s \begin{bmatrix} 
\cos\theta & -\sin\theta \\ 
\sin\theta & \cos\theta 
\end{bmatrix} 
\begin{bmatrix} 
x \\ 
y 
\end{bmatrix} + 
\begin{bmatrix} 
\Delta x \\ 
\Delta y 
\end{bmatrix}
$$

By substituting $a = s\cos\theta$ and $b = s\sin\theta$, the system simplifies to a linear form ideal for least-squares estimation:

$$
\begin{bmatrix} 
x' \\ 
y' 
\end{bmatrix} = 
\begin{bmatrix} 
a & -b \\ 
b & a 
\end{bmatrix} 
\begin{bmatrix} 
x \\ 
y 
\end{bmatrix} + 
\begin{bmatrix} 
\Delta x \\ 
\Delta y 
\end{bmatrix}
$$

### Characteristics
* **How it works:** Minimizes the global objective function $E = \sum \| \mathbf{x'}_i - \mathbf{T}(\mathbf{x}_i) \|^2$ across all Ground Control Points (GCPs).
* **The Result:** Shapes are perfectly preserved. Right angles remain exactly $90^\circ$, parallel lines stay parallel, and aspect ratios are invariant.
* **The Limitation:** It cannot absorb localized distortions (e.g., localized soil settlement, non-uniform paper shrinkage, or localized survey inaccuracies). Localized errors are propagated across the entire dataset as high residual errors.

<table>
  <tr>
    <td align="center"><img src="https://github.com/phisan-chula/2026-Conflation_Sim/blob/main/GlobalSimilarity/RESULT/01_simulation_input.svg" width="280"><br>Figure A</td>
    <td align="center"><img src="https://github.com/phisan-chula/2026-Conflation_Sim/blob/main/GlobalSimilarity/RESULT/02_conflation_optimized.svg" width="280"><br>Figure B</td>
    <td align="center"><img src="[c.svg](https://raw.githubusercontent.com/phisan-chula/2026-Conflation_Sim/4fa14f87cacdd7fadf475ca9e16a7bad0e955c7a/GlobalSimilarity/RESULT/03_topological_snapped.svg)" width="280"><br>Figure C</td>
  </tr>


---

## 2. Local Similarity followed by Global Affine

This is a non-rigid, multi-step optimization framework designed to isolate and eliminate localized discrepancies before standardizing the global coordinate trend.

### Step 1: Local Similarity Adjustment
Geometries or discrete vertex clusters (such as individual boundary segments or separate parcel boundaries like Parcel 1 and Parcel 20) are optimized independently against immediate, local reference points. 

For a local neighborhood $k$, localized parameters are computed:

$$
\mathbf{x'}_k = s_k \mathbf{R}_k \mathbf{x}_k + \mathbf{\Delta}_k
$$

This isolates local survey shifts, regional scaling issues, or physical ground settlement to their true areas of origin.

### Step 2: Global Affine Transformation
Once localized variations are reconciled, a global **Affine Transformation** is applied to tie the entire integrated network to the final target reference system. An affine transform introduces **six parameters**, decoupling the axis scale factors and adding a shearing (skew) component.

The mathematical model is defined as:

$$
\begin{bmatrix} 
x' \\ 
y' 
\end{bmatrix} = 
\begin{bmatrix} 
a_{11} & a_{12} \\ 
a_{21} & a_{22} 
\end{bmatrix} 
\begin{bmatrix} 
x \\ 
y 
\end{bmatrix} + 
\begin{bmatrix} 
x_0 \\ 
y_0 
\end{bmatrix}
$$

Where the transformation matrix decomposes to account for independent scaling ($s_x, s_y$) and shearing ($\gamma$):

$$
\begin{bmatrix} 
a_{11} & a_{12} \\ 
a_{21} & a_{22} 
\end{bmatrix} = 
\begin{bmatrix} 
s_x & 0 \\ 
0 & s_y 
\end{bmatrix}
\begin{bmatrix} 
1 & \tan\gamma \\ 
0 & 1 
\end{bmatrix}
\begin{bmatrix} 
\cos\theta & -\sin\theta \\ 
\sin\theta & \cos\theta 
\end{bmatrix}
$$

### Characteristics
* **The Result:** Parallel lines stay parallel, but right angles can deform slightly ($\gamma \neq 0$) due to directional skew. 
* **The Advantage:** Localized errors are neutralized effectively because they are resolved by the local step or absorbed by the non-uniform directional stretching ($s_x \neq s_y$) of the affine model.

![Vertex Conflation Result (ID 20)](https://raw.githubusercontent.com/phisan-chula/2026-Conflation_Sim/main/LocalSimi_GlobalAffi/RESULT_ID20/04_vertex_conflation_result.svg)

---

## Key Differences at a Glance

| Feature | Global Similarity | Local Similarity + Global Affine |
| :--- | :--- | :--- |
| **Shape Preservation** | **Strict.** No warping, stretching, or shearing. Only global translation, rotation, and uniform scale changes. | **Flexible.** Geometries can stretch, skew, and compress non-uniformly to match localized reference positions. |
| **Handling Local Errors** | **Poor.** Diffuses localized structural errors across the entire grid, yielding higher residual values at control points. | **Excellent.** Counteracts localized distortion directly where the discrepancies occurred. |
| **Geometric Variations** | Internal angles and aspect ratios are perfectly preserved. | Angles can change (skew/shear distortion); scale factors along the $X$ and $Y$ axes can vary ($s_x \neq s_y$). |
| **Degrees of Freedom (DoF)** | $4$ parameters $(\Delta x, \Delta y, \theta, s)$. | Multi-tiered framework culminating in a $6\text{-DoF}$ affine mapping. |
| **Primary Use Cases** | Transforming high-accuracy geodetic coordinates (e.g., rigid Helmert coordinate blocks) where the internal source geometry is flawless. | Rectifying legacy cadastral maps, adjusting complex local survey networks, or compensating for physical ground deformation. |

---

## Physical Intuition

> 💡 **The Glass Analogy (Global Similarity):** > Imagine your spatial layer is drawn on a rigid pane of glass. You can slide it ($\Delta x, \Delta y$), spin it ($\theta$), or look at it through a magnifying lens ($s$), but you can never bend, warp, or distort the lines.

> 💡 **The Rubber Sheet Analogy (Local + Global Affine):** > Imagine your spatial layer is drawn on a flexible sheet of rubber. You map and pin down individual sections locally to match known ground truths, and then apply a final, non-uniform directional pull and skew until every boundary snaps exactly into position.
> 

