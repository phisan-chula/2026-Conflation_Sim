# 2026-Parcel Conflation

# Geometric Warping Approaches: Global Similarity vs. Hybrid Local-Global Affine

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
* **The Limitation:** It cannot absorb localized distortions (e.g., localized soil settlement, non-uniform paper shrinkage, or localized survey inaccuracies). Localized errors are propagated across the entire dataset as high

