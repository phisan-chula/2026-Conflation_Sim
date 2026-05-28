# 2026-Conflation_Sim

Feature,Global Similarity,Local Similarity + Global Affine
Shape Preservation,"Strict. No warping, no stretching, no shearing. Only moves, rotates, and rescales uniformly.","Flexible. Can stretch, skew, and compress different areas to resolve local mismatches."
Handling Local Errors,Poor. Spreads local distortions across the entire map as residual error.,Excellent. Localizes adjustments where distortions actually occurred.
Geometric Changes,Angles and aspect ratios are perfectly preserved.,Angles can change (skew/shear); X and Y scales can differ.
Best Used For...,"Aligning high-accuracy coordinate systems (e.g., standard CRS rotations/shifts) where data shape is trusted.","Rectifying old paper maps, local cadastral adjustments, or ground networks with localized distortion."
